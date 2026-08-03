from datetime import datetime, timedelta
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from t1000.actions import Action
from t1000.env import UniswapV3LPEnv
from t1000.observations import OBS_DIM
from t1000.snapshot import precompute_snapshots
from t1000.tick_math import sqrt_price_x96_from_tick

BASE_TS = pd.Timestamp("2024-01-01", tz="UTC")
N_HOURS = 240  # 10 days of synthetic hourly swaps


def _build_synthetic_dataset(tmp_path):
    rows = []
    block = 1000
    log_index = 0

    def add(event_type, ts, **fields):
        nonlocal block, log_index
        row = {
            "event_type": event_type,
            "block_number": block,
            "log_index": log_index,
            "tx_hash": f"0x{block}",
            "timestamp": ts,
            "tick_lower": np.nan,
            "tick_upper": np.nan,
            "amount": np.nan,
            "amount0": np.nan,
            "amount1": np.nan,
            "sqrt_price_x96": np.nan,
            "liquidity": np.nan,
            "tick": np.nan,
            "owner": None,
        }
        row.update(fields)
        rows.append(row)
        block += 1
        log_index += 1

    # tick ~200000 is the realistic historical range for this pool's USDC(6
    # decimals)/WETH(18 decimals) convention -- oscillating near tick 0 would
    # imply an ~10^12x wrong USD/ETH price and break the liquidity/value math.
    BASE_TICK = 200000
    add("Mint", BASE_TS, tick_lower=BASE_TICK - 5000, tick_upper=BASE_TICK + 5000, amount=10_000_000, owner="0xseed")

    tick = BASE_TICK
    rng = np.random.default_rng(42)
    for h in range(1, N_HOURS + 1):
        ts = BASE_TS + timedelta(hours=h)
        step = int(rng.integers(-5, 6)) * 10
        new_tick = int(np.clip(tick + step, BASE_TICK - 2000, BASE_TICK + 2000))
        zero_for_one = new_tick < tick
        add(
            "Swap",
            ts,
            amount0=1_000_000 if zero_for_one else -900_000,
            amount1=-900_000_000_000_000 if zero_for_one else 1_000_000_000_000_000,
            sqrt_price_x96=sqrt_price_x96_from_tick(new_tick),
            liquidity=10_000_000,
            tick=new_tick,
        )
        tick = new_tick

    events_df = pd.DataFrame(rows).sort_values(["block_number", "log_index"]).reset_index(drop=True)

    gas_rows = []
    for h in range(0, N_HOURS + 1):
        gas_rows.append({"block_number": 1000 + h, "block_timestamp": BASE_TS + timedelta(hours=h), "base_fee_per_gas": 30e9})
    gas_df = pd.DataFrame(gas_rows)

    records = [
        SimpleNamespace(event_type=r["event_type"], timestamp=r["timestamp"], fields={
            k: v for k, v in r.items()
            if k not in ("event_type", "block_number", "log_index", "tx_hash", "timestamp", "owner")
            and not (isinstance(v, float) and np.isnan(v))
        })
        for r in rows
    ]
    snapshot_dir = tmp_path / "snapshots"
    index = precompute_snapshots(records, snapshot_dir, cadence_seconds=3600 * 24)

    swaps_df = events_df[events_df.event_type == "Swap"].reset_index(drop=True)
    return events_df, gas_df, swaps_df, index


@pytest.fixture
def env(tmp_path):
    events_df, gas_df, swaps_df, index = _build_synthetic_dataset(tmp_path)
    start_ts = BASE_TS
    end_ts = BASE_TS + timedelta(hours=N_HOURS)
    return UniswapV3LPEnv(
        events_df=events_df,
        gas_df=gas_df,
        swaps_df=swaps_df,
        snapshot_index=index,
        start_ts=start_ts,
        end_ts=end_ts,
        episode_hours=48,
        step_hours=1.0,
        initial_notional_usd=10_000.0,
    )


def test_reset_returns_valid_observation(env):
    obs, info = env.reset(seed=0)
    assert obs.shape == (OBS_DIM,)
    assert obs.dtype == np.float32
    assert np.all(np.isfinite(obs))
    assert info == {}


def test_step_hold_returns_valid_transition(env):
    env.reset(seed=0)
    obs, reward, terminated, truncated, info = env.step(Action.HOLD)
    assert obs.shape == (OBS_DIM,)
    assert np.isfinite(reward)
    assert terminated is False
    assert isinstance(truncated, (bool, np.bool_))
    assert "portfolio_value_usd" in info


def test_episode_truncates_after_episode_hours(env):
    env.reset(seed=1)
    truncated = False
    steps = 0
    while not truncated and steps < 100:
        _, _, _, truncated, _ = env.step(Action.HOLD)
        steps += 1
    assert truncated
    assert steps == 48


def test_rebalance_opens_a_position_and_spends_cash(env):
    env.reset(seed=2)
    cash_before = env.cash_usd
    assert env.position_tick_lower is None
    env.step(Action.REBALANCE_MEDIUM)
    assert env.position_tick_lower is not None
    assert env.position_tick_upper is not None
    # invests all but a small gas reserve (see CASH_RESERVE_FRACTION) into the position
    assert 0 < env.cash_usd < cash_before


def test_exit_to_cash_closes_position(env):
    env.reset(seed=3)
    env.step(Action.REBALANCE_MEDIUM)
    assert env.position_tick_lower is not None
    env.step(Action.EXIT_TO_CASH)
    assert env.position_tick_lower is None
    assert env.cash_usd > 0


def test_hold_action_is_free_of_gas_cost(env):
    env.reset(seed=4)
    _, _, _, _, info = env.step(Action.HOLD)
    assert info["gas_cost_usd"] == 0.0


def test_rebalance_action_incurs_gas_cost(env):
    env.reset(seed=5)
    _, _, _, _, info = env.step(Action.REBALANCE_MEDIUM)
    assert info["gas_cost_usd"] > 0.0


def test_insufficient_cash_blocks_action_instead_of_going_negative(env):
    env.reset(seed=6)
    env.cash_usd = 0.01  # not enough to pay for any gas-incurring action
    obs_before = env._build_obs()
    _, _, _, _, info = env.step(Action.REBALANCE_WIDE)
    assert info["gas_cost_usd"] == 0.0
    assert env.cash_usd >= 0.0
    assert env.position_tick_lower is None  # action was a no-op, position never opened


def test_reset_is_reproducible_with_same_seed(env):
    obs1, _ = env.reset(seed=123)
    start_ts_1 = env.episode_start_ts
    obs2, _ = env.reset(seed=123)
    start_ts_2 = env.episode_start_ts
    assert start_ts_1 == start_ts_2
    np.testing.assert_array_equal(obs1, obs2)


def test_volatility_features_do_not_saturate(env):
    """Regression: the env used to feed raw USD prices where the observation
    builder expects log returns, pinning both volatility features at the 1.0
    clip from the second step onward."""
    from t1000.observations import FEATURE_NAMES

    vol_24h_idx = FEATURE_NAMES.index("volatility_24h")
    vol_7d_idx = FEATURE_NAMES.index("volatility_7d")

    env.reset(seed=7)
    obs = None
    for _ in range(30):
        obs, _, _, _, _ = env.step(Action.HOLD)

    assert 0.0 < obs[vol_24h_idx] < 1.0
    assert 0.0 < obs[vol_7d_idx] < 1.0
    # hourly log returns of a few tens of ticks are well under the vol scale
    assert max(abs(r) for r in env.return_history) < 0.05


def test_open_position_with_zero_liquidity_does_not_burn_cash(env):
    """Regression: a degenerate range used to debit the invested cash while
    opening a position worth nothing, evaporating the capital."""
    env.reset(seed=8)
    cash_before = env.cash_usd
    tick = env.engine.pool.tick
    env._open_position(tick, tick)  # zero-width range -> zero liquidity
    assert env.position_tick_lower is None
    assert env.cash_usd == cash_before


def test_rebalance_from_cash_incurs_swap_cost(env):
    """Regression: opening/closing a position used to convert between cash
    and the position's token0/token1 mix at mid price, with no pool fee or
    slippage. A range centered on the current tick needs both tokens, so
    funding it from pure cash must cost something."""
    env.reset(seed=14)
    _, _, _, _, info = env.step(Action.REBALANCE_MEDIUM)
    assert info["swap_cost_usd"] > 0.0


def test_exit_to_cash_incurs_swap_cost(env):
    """Regression: exiting to cash used to be a free mid-price conversion;
    the WETH-denominated side of the closed position must be swapped away."""
    env.reset(seed=15)
    env.step(Action.REBALANCE_MEDIUM)
    _, _, _, _, info = env.step(Action.EXIT_TO_CASH)
    assert info["swap_cost_usd"] > 0.0


def test_hold_and_collect_are_free_of_swap_cost(env):
    env.reset(seed=16)
    env.step(Action.REBALANCE_MEDIUM)
    _, _, _, _, info_hold = env.step(Action.HOLD)
    assert info_hold["swap_cost_usd"] == 0.0
    _, _, _, _, info_collect = env.step(Action.COLLECT)
    assert info_collect["swap_cost_usd"] == 0.0


def test_rebalance_to_same_range_only_charges_the_composition_delta(env):
    """A rebalance into an (almost) identical range shouldn't cost as much
    as funding the same range from scratch: the swap cost must be netted
    against what was already held, not charged on the full notional."""
    env.reset(seed=17)
    _, _, _, _, info_first = env.step(Action.REBALANCE_MEDIUM)
    _, _, _, _, info_again = env.step(Action.REBALANCE_MEDIUM)
    assert 0.0 <= info_again["swap_cost_usd"] < info_first["swap_cost_usd"]


def test_unclaimed_fees_use_current_price_not_accrual_time_price(env):
    """Regression: unclaimed_fees_usd used to be a running total frozen at
    each fee chunk's accrual-time USD price; it must instead be the
    uncollected token amounts revalued at the CURRENT price on every read."""
    env.reset(seed=13)
    env.step(Action.REBALANCE_MEDIUM)
    # 20 steps (not e.g. 5): the synthetic price random-walks in both
    # directions, and Uniswap V3 only accrues a swap's fee in the token
    # being sold, so a short run can land on one side purely by chance --
    # need enough steps for both fee_growth0 and fee_growth1 to move.
    for _ in range(20):
        env.step(Action.HOLD)
    assert env.unclaimed_fee_amount1 > 0.0  # some WETH-denominated fee accrued

    price = env._current_price()
    expected = env.unclaimed_fee_amount0 + env.unclaimed_fee_amount1 * price
    assert env.unclaimed_fees_usd == pytest.approx(expected)

    # Bump the pool price directly, with no new fee accrual: a frozen-USD
    # implementation would leave unclaimed_fees_usd unchanged here.
    fees_before = env.unclaimed_fees_usd
    env.engine.pool.sqrt_price_x96 = int(env.engine.pool.sqrt_price_x96 * 1.05)
    bumped_price = env._current_price()
    assert env.unclaimed_fees_usd == pytest.approx(
        env.unclaimed_fee_amount0 + env.unclaimed_fee_amount1 * bumped_price
    )
    assert env.unclaimed_fees_usd != pytest.approx(fees_before)


@pytest.fixture
def benchrel_env(tmp_path):
    events_df, gas_df, swaps_df, index = _build_synthetic_dataset(tmp_path)
    return UniswapV3LPEnv(
        events_df=events_df,
        gas_df=gas_df,
        swaps_df=swaps_df,
        snapshot_index=index,
        start_ts=BASE_TS,
        end_ts=BASE_TS + timedelta(hours=N_HOURS),
        episode_hours=48,
        step_hours=1.0,
        initial_notional_usd=10_000.0,
        reward_mode="benchmark_relative",
    )


def test_invalid_reward_mode_raises(tmp_path):
    events_df, gas_df, swaps_df, index = _build_synthetic_dataset(tmp_path)
    with pytest.raises(ValueError, match="reward_mode"):
        UniswapV3LPEnv(
            events_df=events_df,
            gas_df=gas_df,
            swaps_df=swaps_df,
            snapshot_index=index,
            start_ts=BASE_TS,
            end_ts=BASE_TS + timedelta(hours=N_HOURS),
            reward_mode="relative",
        )


def test_benchmark_relative_reward_is_zero_while_fully_in_cash(benchrel_env):
    """All-cash portfolio has no price exposure: both the portfolio and its
    HODL benchmark are flat, so a HOLD step must reward exactly 0 no matter
    what the price did."""
    benchrel_env.reset(seed=9)
    for _ in range(5):
        _, reward, _, _, _ = benchrel_env.step(Action.HOLD)
        assert reward == 0.0


def test_benchmark_relative_reward_subtracts_weth_price_exposure(benchrel_env):
    """With a position open, the reward must equal the absolute-mode reward
    minus (start-of-step WETH exposure x price change) -- i.e. holding
    through a price move scores ~0, not the move itself. Exposure includes
    both the position's WETH side and any uncollected WETH-denominated fees,
    since both float with price."""
    benchrel_env.reset(seed=10)
    benchrel_env.step(Action.REBALANCE_WIDE)
    assert benchrel_env.position_tick_lower is not None

    for _ in range(10):
        weth_before = benchrel_env._position_weth_amount() + benchrel_env.unclaimed_fee_amount1
        price_before = benchrel_env.prev_price
        pv_before = benchrel_env._portfolio_value_usd()
        _, reward, _, _, info = benchrel_env.step(Action.HOLD)
        absolute_reward = (info["portfolio_value_usd"] - pv_before) / benchrel_env.initial_notional_usd
        expected = absolute_reward - weth_before * (info["price_usd"] - price_before) / benchrel_env.initial_notional_usd
        assert reward == pytest.approx(expected, abs=1e-12)


def _make_env(dataset, **kwargs):
    events_df, gas_df, swaps_df, index = dataset
    params = dict(
        events_df=events_df,
        gas_df=gas_df,
        swaps_df=swaps_df,
        snapshot_index=index,
        start_ts=BASE_TS,
        end_ts=BASE_TS + timedelta(hours=N_HOURS),
        episode_hours=48,
        step_hours=1.0,
        initial_notional_usd=10_000.0,
    )
    params.update(kwargs)
    return UniswapV3LPEnv(**params)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"width_scale": 0.0},
        {"width_scale": -1.0},
        {"gas_multiplier": -0.1},
        {"vol_lookback_short_hours": 336.0, "vol_lookback_long_hours": 168.0},
        {"vol_lookback_short_hours": 0.0},
        {"market_stats_start": BASE_TS},  # market_stats_end missing
        {"hedge_enabled": True},  # funding_df missing
    ],
)
def test_invalid_sweep_knobs_raise(tmp_path, kwargs):
    dataset = _build_synthetic_dataset(tmp_path)
    with pytest.raises(ValueError):
        _make_env(dataset, **kwargs)


def test_width_scale_narrows_opened_range(tmp_path):
    dataset = _build_synthetic_dataset(tmp_path)
    widths = {}
    for scale in (1.0, 0.5):
        env = _make_env(dataset, width_scale=scale)
        env.reset(seed=11)
        env.step(Action.REBALANCE_MEDIUM)
        widths[scale] = env.position_tick_upper - env.position_tick_lower
    assert 0 < widths[0.5] < widths[1.0]
    # tick span is ~log-linear in price width, so half the pct width should
    # land near half the tick span (spacing rounding allows some slack)
    assert widths[0.5] == pytest.approx(widths[1.0] / 2, rel=0.1)


def test_gas_multiplier_scales_gas_cost(tmp_path):
    dataset = _build_synthetic_dataset(tmp_path)
    costs = {}
    for mult in (1.0, 3.0):
        env = _make_env(dataset, gas_multiplier=mult)
        env.reset(seed=12)
        _, _, _, _, info = env.step(Action.REBALANCE_MEDIUM)
        costs[mult] = info["gas_cost_usd"]
    assert costs[1.0] > 0
    assert costs[3.0] == pytest.approx(3 * costs[1.0])


def test_market_stats_start_end_scopes_stats_to_window(tmp_path):
    """Regression: MarketStats used to always be computed from the full
    swaps_df/gas_df the caller passed in, leaking distributional stats about
    periods (e.g. a holdout window) the env itself never replays -- e.g.
    train.py passed the entire 14-month dataset while only training on
    months 1-8. market_stats_start/end must restrict what MarketStats sees."""
    dataset = _build_synthetic_dataset(tmp_path)
    full_env = _make_env(dataset)
    scoped_env = _make_env(
        dataset,
        market_stats_start=BASE_TS,
        market_stats_end=BASE_TS + timedelta(hours=24),
    )
    assert len(scoped_env.market_stats._sorted_base_fees) < len(full_env.market_stats._sorted_base_fees)


def _make_funding_df(rate=0.0001, start=BASE_TS, hours=N_HOURS, period_hours=8.0):
    n_periods = int(hours / period_hours) + 2
    timestamps = [start + timedelta(hours=period_hours * i) for i in range(n_periods)]
    return pd.DataFrame({"timestamp": timestamps, "funding_rate": [rate] * len(timestamps)})


def test_hedge_enabled_with_benchmark_relative_raises(tmp_path):
    dataset = _build_synthetic_dataset(tmp_path)
    with pytest.raises(ValueError, match="benchmark_relative"):
        _make_env(
            dataset,
            hedge_enabled=True,
            funding_df=_make_funding_df(),
            reward_mode="benchmark_relative",
        )


def test_hedge_pnl_zero_while_fully_in_cash(tmp_path):
    """No position ever opens (all HOLD), so prev_weth_exposure stays 0 the
    whole episode: a short sized to zero exposure has zero price P&L and
    zero funding, regardless of the funding rate or price path."""
    dataset = _build_synthetic_dataset(tmp_path)
    hedge_env = _make_env(dataset, hedge_enabled=True, funding_df=_make_funding_df(rate=0.0005))
    hedge_env.reset(seed=20)
    for _ in range(5):
        _, _, _, _, info = hedge_env.step(Action.HOLD)
        assert info["hedge_pnl_usd"] == 0.0
        assert info["hedge_funding_usd"] == 0.0


def test_hedge_does_not_change_lp_mechanics_only_cash(tmp_path):
    """hedge_margin_usd is a segregated ledger (see the P0-style bug this
    fixed: a losing hedge used to drain cash_usd itself, starving gas and
    stranding the position out of range -- caught by a real-data smoke test
    during development, see the delta-hedge plan). Because of that
    separation, cash_usd -- and therefore every LP-mechanics quantity that
    depends on it, like _open_position's investable sizing -- must be
    *exactly* identical between hedge on/off regardless of how many times
    the action sequence rebalances; only hedge_margin_usd and
    portfolio_value_usd may differ."""
    dataset = _build_synthetic_dataset(tmp_path)
    plain_env = _make_env(dataset)
    hedge_env = _make_env(dataset, hedge_enabled=True, funding_df=_make_funding_df(rate=0.0003))
    plain_env.reset(seed=21)
    hedge_env.reset(seed=21)

    actions = [
        Action.REBALANCE_WIDE, Action.HOLD, Action.HOLD, Action.COLLECT, Action.HOLD,
        Action.SHIFT_UP, Action.HOLD, Action.REBALANCE_NARROW, Action.HOLD, Action.EXIT_TO_CASH,
        Action.HOLD, Action.REBALANCE_MEDIUM, Action.HOLD,
    ]
    cumulative_hedge_pnl = 0.0
    for action in actions:
        _, _, _, _, plain_info = plain_env.step(action)
        _, _, _, _, hedge_info = hedge_env.step(action)
        cumulative_hedge_pnl += hedge_info["hedge_pnl_usd"]

        assert hedge_env.cash_usd == pytest.approx(plain_env.cash_usd)
        assert hedge_env.position_tick_lower == plain_env.position_tick_lower
        assert hedge_env.position_tick_upper == plain_env.position_tick_upper
        assert hedge_env.position_liquidity == pytest.approx(plain_env.position_liquidity)
        assert hedge_env.unclaimed_fee_amount0 == pytest.approx(plain_env.unclaimed_fee_amount0)
        assert hedge_env.unclaimed_fee_amount1 == pytest.approx(plain_env.unclaimed_fee_amount1)
        assert hedge_info["gas_cost_usd"] == pytest.approx(plain_info["gas_cost_usd"])
        assert hedge_info["swap_cost_usd"] == pytest.approx(plain_info["swap_cost_usd"])
        assert hedge_env.hedge_margin_usd == pytest.approx(cumulative_hedge_pnl)


def test_hedge_price_pnl_matches_prev_exposure_times_price_change(tmp_path):
    """With funding held at 0, hedge_pnl_usd must equal exactly
    -prev_exposure_weth * price_change_usd -- the same term
    benchmark_relative subtracts from the reward, now flowing into cash."""
    dataset = _build_synthetic_dataset(tmp_path)
    hedge_env = _make_env(dataset, hedge_enabled=True, funding_df=_make_funding_df(rate=0.0))
    hedge_env.reset(seed=22)
    hedge_env.step(Action.REBALANCE_WIDE)
    assert hedge_env.position_tick_lower is not None

    for _ in range(10):
        weth_before = hedge_env._position_weth_amount() + hedge_env.unclaimed_fee_amount1
        price_before = hedge_env.prev_price
        _, _, _, _, info = hedge_env.step(Action.HOLD)
        expected_price_pnl = -weth_before * (info["price_usd"] - price_before)
        assert info["hedge_pnl_usd"] == pytest.approx(expected_price_pnl, abs=1e-9)
        assert info["hedge_funding_usd"] == 0.0


@pytest.mark.parametrize("rate,expect_positive", [(0.0005, True), (-0.0005, False)])
def test_hedge_funding_sign_matches_rate_direction(tmp_path, rate, expect_positive):
    """A positive funding rate means longs pay shorts -- the hedge (short)
    earns funding; a negative rate means the hedge pays."""
    dataset = _build_synthetic_dataset(tmp_path)
    hedge_env = _make_env(dataset, hedge_enabled=True, funding_df=_make_funding_df(rate=rate))
    hedge_env.reset(seed=23)
    hedge_env.step(Action.REBALANCE_WIDE)
    assert hedge_env.position_tick_lower is not None
    _, _, _, _, info = hedge_env.step(Action.HOLD)
    assert (info["hedge_funding_usd"] > 0) == expect_positive


def test_hedge_funding_amortized_by_step_hours(tmp_path):
    """Funding scales linearly with step_hours / FUNDING_PERIOD_HOURS.
    Calls _hedge_funding_usd directly with a fixed exposure rather than
    driving two envs through step() with different step_hours: a 4h step
    replays 4x the on-chain events of a 1h step before an action even runs,
    so the two envs' actual exposures would diverge for reasons unrelated
    to the amortization formula being tested here."""
    dataset = _build_synthetic_dataset(tmp_path)
    funding_df = _make_funding_df(rate=0.0006)
    env_1h = _make_env(dataset, hedge_enabled=True, funding_df=funding_df, step_hours=1.0)
    env_4h = _make_env(dataset, hedge_enabled=True, funding_df=funding_df, step_hours=4.0)
    env_1h.reset(seed=24)
    env_4h.reset(seed=24)
    exposure = 1.5
    price = env_1h._current_price()
    funding_1h = env_1h._hedge_funding_usd(exposure, price)
    funding_4h = env_4h._hedge_funding_usd(exposure, price)
    assert funding_4h == pytest.approx(4 * funding_1h)


def test_hedge_tracks_exposure_after_exit_to_cash(tmp_path):
    """The hedge unwinds automatically by resizing to prev_weth_exposure
    each step -- no explicit close branch is needed in _apply_action. This
    locks that design decision in: after EXIT_TO_CASH, the next step's
    hedge P&L/funding must both be exactly 0."""
    dataset = _build_synthetic_dataset(tmp_path)
    hedge_env = _make_env(dataset, hedge_enabled=True, funding_df=_make_funding_df(rate=0.0005))
    hedge_env.reset(seed=25)
    hedge_env.step(Action.REBALANCE_WIDE)
    hedge_env.step(Action.EXIT_TO_CASH)
    assert hedge_env.position_tick_lower is None
    _, _, _, _, info = hedge_env.step(Action.HOLD)
    assert info["hedge_pnl_usd"] == 0.0
    assert info["hedge_funding_usd"] == 0.0


def test_current_funding_rate_uses_at_or_before_lookup(tmp_path):
    dataset = _build_synthetic_dataset(tmp_path)
    funding_df = pd.DataFrame({
        "timestamp": [BASE_TS, BASE_TS + timedelta(hours=2)],
        "funding_rate": [0.0001, 0.0009],
    })
    hedge_env = _make_env(dataset, hedge_enabled=True, funding_df=funding_df)
    hedge_env.current_ts = BASE_TS + timedelta(hours=1)
    assert hedge_env._current_funding_rate() == pytest.approx(0.0001)
    hedge_env.current_ts = BASE_TS + timedelta(hours=3)
    assert hedge_env._current_funding_rate() == pytest.approx(0.0009)
    hedge_env.current_ts = BASE_TS - timedelta(hours=1)
    assert hedge_env._current_funding_rate() == pytest.approx(0.0001)
