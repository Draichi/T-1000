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
