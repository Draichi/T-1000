"""Gymnasium environment for the Uniswap V3 concentrated-liquidity LP agent.

Portfolio accounting is deliberately simple: `portfolio_value_usd = cash_usd +
position_value_usd + unclaimed_fees_usd + hedge_margin_usd`. The per-step
reward is just the change in this single number (scaled by the initial
notional) -- fees earned, impermanent loss, gas, and swap costs are all
*already* reflected in it (fees raise unclaimed_fees_usd, gas/swap costs
reduce cash_usd, IL shows up as the position's mark-to-market moving
differently than cash would have), so there's no need to compute
"fees - IL - gas" as three separate terms that could double-count.
unclaimed_fees_usd is itself computed live (see the property below): its
WETH-denominated portion floats with price until COLLECT, exactly like the
position itself. hedge_margin_usd (when hedge_enabled) is a segregated
running P&L for the short-perp hedge, deliberately kept out of cash_usd so a
losing hedge can never strand the LP position by starving its gas reserve --
always 0.0 when hedge_enabled=False.
"""
from typing import Optional

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces

from . import constants
from .actions import Action, N_ACTIONS, gas_components_for_action, target_range_for_action
from .fee_engine import FeeEngine
from .gas_model import DEFAULT_GAS_UNITS, action_gas_cost_usd
from .il import position_value_usd
from .observations import OBS_DIM, ObservationInputs, build_observation
from .snapshot import SnapshotIndex, apply_event, load_snapshot
from .tick_math import human_price_usd_per_eth, sqrt_price_x96_from_tick

Q96 = 2**96
CASH_RESERVE_FRACTION = 0.02  # kept aside as a gas buffer whenever a position is opened
# Opening/closing/exiting a position generally requires trading part of the
# notional from one token to the other to hit the required composition --
# modeled as a single swap through the pool at the current fee tier, plus a
# small estimated price-impact allowance (this position is tiny relative to
# real ETH/USDC 0.05% depth, so slippage is a minor addition to the fee).
SWAP_FEE_RATE = constants.FEE_PIPS / 1_000_000
SWAP_SLIPPAGE_RATE = 0.0002
# Real perpetual funding settles every 8h; amortized over step_hours-length
# steps rather than applied as a lump payment on the exact settlement hour,
# same simplification tier as SWAP_SLIPPAGE_RATE above.
FUNDING_PERIOD_HOURS = 8.0


def _to_utc_timestamp(ts) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def _apply_row(engine: FeeEngine, row) -> None:
    if row.event_type == "Mint":
        engine.apply_mint(int(row.tick_lower), int(row.tick_upper), int(row.amount))
    elif row.event_type == "Burn":
        engine.apply_burn(int(row.tick_lower), int(row.tick_upper), int(row.amount))
    elif row.event_type == "Swap":
        engine.apply_swap(int(row.amount0), int(row.amount1), int(row.sqrt_price_x96), int(row.tick), int(row.liquidity))


def _liquidity_for_budget(budget_usd, sqrt_price_x96, tick_lower, tick_upper, usd_per_eth) -> float:
    from .tick_math import amounts_for_liquidity

    sqrt_p = sqrt_price_x96 / Q96
    sqrt_lo = sqrt_price_x96_from_tick(tick_lower) / Q96
    sqrt_hi = sqrt_price_x96_from_tick(tick_upper) / Q96
    unit0, unit1 = amounts_for_liquidity(1.0, sqrt_p, sqrt_lo, sqrt_hi)
    value_per_unit_liquidity = unit0 / 10**6 + unit1 / 10**18 * usd_per_eth
    if value_per_unit_liquidity <= 0:
        return 0.0
    return budget_usd / value_per_unit_liquidity


class MarketStats:
    """Precomputed once from the training data: hourly volume log1p mean/std
    (for the observation's volume z-score) and a sorted base_fee_per_gas
    array (for a cheap percentile lookup)."""

    def __init__(self, swaps_df: pd.DataFrame, gas_df: pd.DataFrame):
        price = swaps_df["sqrt_price_x96"].astype(float).apply(human_price_usd_per_eth)
        zero_for_one = swaps_df["amount0"].astype(float) > 0
        volume_usd = np.where(
            zero_for_one,
            swaps_df["amount0"].astype(float).abs() / 10**6,
            swaps_df["amount1"].astype(float).abs() / 10**18 * price,
        )
        volume_series = pd.Series(volume_usd, index=pd.DatetimeIndex(swaps_df["timestamp"]))
        hourly_volume = volume_series.resample("1h").sum()
        log_volume = np.log1p(hourly_volume.clip(lower=0))
        self.volume_log_mean = float(log_volume.mean()) if len(log_volume) else 0.0
        self.volume_log_std = float(log_volume.std()) if len(log_volume) else 0.0
        self._sorted_base_fees = np.sort(gas_df["base_fee_per_gas"].dropna().to_numpy())

    def gas_percentile(self, base_fee: float) -> float:
        if len(self._sorted_base_fees) == 0:
            return 0.5
        rank = np.searchsorted(self._sorted_base_fees, base_fee, side="right")
        return float(rank / len(self._sorted_base_fees))


class UniswapV3LPEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        events_df: pd.DataFrame,
        gas_df: pd.DataFrame,
        swaps_df: pd.DataFrame,
        snapshot_index: SnapshotIndex,
        start_ts,
        end_ts,
        episode_hours: int = 720,
        step_hours: float = 1.0,
        initial_notional_usd: float = 10_000.0,
        reward_mode: str = "absolute",
        width_scale: float = 1.0,
        gas_multiplier: float = 1.0,
        vol_lookback_short_hours: float = 24.0,
        vol_lookback_long_hours: float = 168.0,
        market_stats_start=None,
        market_stats_end=None,
        hedge_enabled: bool = False,
        funding_df: Optional[pd.DataFrame] = None,
    ):
        super().__init__()
        if reward_mode not in ("absolute", "benchmark_relative"):
            raise ValueError(f"unknown reward_mode: {reward_mode!r}")
        if hedge_enabled and reward_mode == "benchmark_relative":
            raise ValueError(
                "hedge_enabled is incompatible with reward_mode='benchmark_relative' "
                "(the real hedge already neutralizes ETH beta via cash_usd; "
                "benchmark_relative would subtract the same term again)"
            )
        if hedge_enabled and funding_df is None:
            raise ValueError("hedge_enabled=True requires funding_df")
        if width_scale <= 0:
            raise ValueError(f"width_scale must be > 0, got {width_scale}")
        if gas_multiplier < 0:
            raise ValueError(f"gas_multiplier must be >= 0, got {gas_multiplier}")
        if not 0 < vol_lookback_short_hours <= vol_lookback_long_hours:
            raise ValueError(
                "need 0 < vol_lookback_short_hours <= vol_lookback_long_hours, "
                f"got {vol_lookback_short_hours} / {vol_lookback_long_hours}"
            )
        if (market_stats_start is None) != (market_stats_end is None):
            raise ValueError("market_stats_start and market_stats_end must be given together")
        self.reward_mode = reward_mode
        self.width_scale = width_scale
        self.gas_multiplier = gas_multiplier
        # Standardize on tz-aware UTC, ns precision: real (BigQuery-sourced) data is
        # tz-aware, synthetic/test data is often naive, and episode/step timestamps
        # involve fractional-hour arithmetic (random reset offsets) that naturally
        # produces ns-resolution Timestamps -- pandas won't silently truncate a
        # finer-resolution Timestamp, or compare tz-aware against tz-naive, so both
        # need to be forced into the same representation up front.
        self.events_df = events_df.assign(
            timestamp=pd.to_datetime(events_df["timestamp"], utc=True).dt.as_unit("ns")
        )
        # reset()/step() locate their event slice via Series.searchsorted
        # (binary search) instead of an O(N) boolean mask, which requires
        # events_df to already be in (block, log_index) order -- true of
        # every real on-chain event log and the on-disk parquet it's read
        # from, asserted here rather than silently re-sorted so an upstream
        # data bug fails loudly instead of reordering replay.
        if not self.events_df["timestamp"].is_monotonic_increasing:
            raise ValueError("events_df must be sorted by timestamp (block, log_index order)")
        self.gas_df = gas_df.assign(
            block_timestamp=pd.to_datetime(gas_df["block_timestamp"], utc=True).dt.as_unit("ns")
        )
        self.gas_df = self.gas_df.sort_values("block_timestamp").reset_index(drop=True)
        self.hedge_enabled = hedge_enabled
        if funding_df is not None:
            self.funding_df = funding_df.assign(
                timestamp=pd.to_datetime(funding_df["timestamp"], utc=True).dt.as_unit("ns")
            ).sort_values("timestamp").reset_index(drop=True)
        else:
            self.funding_df = None
        self.snapshot_index = snapshot_index
        self.start_ts = _to_utc_timestamp(start_ts)
        self.end_ts = _to_utc_timestamp(end_ts)
        # Real on-chain events never extend past this; an episode that runs
        # beyond it would silently replay a frozen market (no swaps, no fee
        # accrual) instead of ending, see step()'s truncation check below.
        self.data_end_ts = self.events_df["timestamp"].max()
        self.episode_hours = episode_hours
        self.step_hours = step_hours
        # return_history holds one log return per *step*, so hour-denominated
        # lookbacks must be converted (at step_hours=1 they're identical).
        self._vol_lookback_short_steps = max(2, round(vol_lookback_short_hours / step_hours))
        self._vol_lookback_long_steps = max(2, round(vol_lookback_long_hours / step_hours))
        self.initial_notional_usd = initial_notional_usd
        # By default MarketStats is computed from whatever swaps_df/gas_df the
        # caller passed in -- fine when that's already scoped to the training
        # window, but a caller (e.g. a backtest loading the full dataset)
        # that wants stats matching a *different* window than start_ts/end_ts
        # (typically: the window the loaded checkpoint was actually trained
        # on, so live observation normalization matches training) can pass
        # market_stats_start/end explicitly to filter before computing.
        stats_swaps, stats_gas = swaps_df, self.gas_df
        if market_stats_start is not None:
            stats_start = _to_utc_timestamp(market_stats_start)
            stats_end = _to_utc_timestamp(market_stats_end)
            swaps_ts = pd.to_datetime(swaps_df["timestamp"], utc=True)
            stats_swaps = swaps_df[(swaps_ts >= stats_start) & (swaps_ts <= stats_end)]
            stats_gas = self.gas_df[
                (self.gas_df["block_timestamp"] >= stats_start) & (self.gas_df["block_timestamp"] <= stats_end)
            ]
        self.market_stats = MarketStats(stats_swaps, stats_gas)

        self.action_space = spaces.Discrete(N_ACTIONS)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(OBS_DIM,), dtype=np.float32)

        self._np_random_local = np.random.default_rng()

        # episode-scoped state, set in reset()
        self.engine: Optional[FeeEngine] = None
        self.position_tick_lower = None
        self.position_tick_upper = None
        self.position_liquidity = 0.0
        self.fee_checkpoint = (0, 0)
        self.unclaimed_fee_amount0 = 0.0
        self.unclaimed_fee_amount1 = 0.0
        self.cash_usd = initial_notional_usd
        # Running P&L of the perp hedge, tracked separately from cash_usd
        # (a segregated margin account, like a real trader would keep) --
        # otherwise a losing hedge (e.g. a short during a rally) drains the
        # same reserve that pays gas, stranding the LP position out of
        # range with no way to rebalance back in. Included in
        # _portfolio_value_usd(); always 0.0 when hedge_enabled=False.
        self.hedge_margin_usd = 0.0
        self.hours_since_rebalance = 0.0
        self.return_history: list = []  # per-step log returns of the pool price
        self.volume_history: list = []
        self.current_ts = None
        self.episode_end_ts = None
        self.episode_start_ts = None
        self.price_at_episode_start = None
        self.prev_price = None
        self.prev_portfolio_value = None
        self.prev_weth_exposure = 0.0

    def _current_price(self) -> float:
        return human_price_usd_per_eth(self.engine.pool.sqrt_price_x96)

    def _current_base_fee(self) -> float:
        idx = self.gas_df["block_timestamp"].searchsorted(self.current_ts, side="right") - 1
        idx = max(0, min(idx, len(self.gas_df) - 1))
        return float(self.gas_df["base_fee_per_gas"].iloc[idx])

    def _current_funding_rate(self) -> float:
        idx = self.funding_df["timestamp"].searchsorted(self.current_ts, side="right") - 1
        idx = max(0, min(idx, len(self.funding_df) - 1))
        return float(self.funding_df["funding_rate"].iloc[idx])

    def _funding_rate_for_step(self) -> float:
        return self._current_funding_rate() * (self.step_hours / FUNDING_PERIOD_HOURS)

    def _position_value_usd(self) -> float:
        if self.position_tick_lower is None:
            return 0.0
        value, _, _ = position_value_usd(
            self.position_liquidity,
            self.engine.pool.sqrt_price_x96,
            self.position_tick_lower,
            self.position_tick_upper,
            self._current_price(),
        )
        return value

    @property
    def unclaimed_fees_usd(self) -> float:
        """Accrued-but-uncollected fees, revalued at the CURRENT price on
        every read: the token0 (USDC) portion is already dollar-stable, but
        the token1 (WETH) portion must float with price like the rest of the
        position until COLLECT actually withdraws it -- it is not converted
        to cash at accrual time."""
        return self.unclaimed_fee_amount0 + self.unclaimed_fee_amount1 * self._current_price()

    def _portfolio_value_usd(self) -> float:
        return self.cash_usd + self._position_value_usd() + self.unclaimed_fees_usd + self.hedge_margin_usd

    def _position_amount1_usd(self) -> float:
        """USD value of the position's WETH-denominated side (0 if no
        position); used to net the swap cost of a close/rebalance against
        what it's replacing, so only the actual composition change is
        charged, not the full notional."""
        return self._position_weth_amount() * self._current_price()

    def _swap_cost_usd(self, notional_usd: float) -> float:
        return max(notional_usd, 0.0) * (SWAP_FEE_RATE + SWAP_SLIPPAGE_RATE)

    def _position_weth_amount(self) -> float:
        """Human-unit WETH currently held inside the position (excludes
        unclaimed fees -- see _total_weth_exposure for the portfolio-wide
        figure)."""
        if self.position_tick_lower is None:
            return 0.0
        _, _, amount1_human = position_value_usd(
            self.position_liquidity,
            self.engine.pool.sqrt_price_x96,
            self.position_tick_lower,
            self.position_tick_upper,
            self._current_price(),
        )
        return amount1_human

    def _total_weth_exposure(self) -> float:
        """Total human-unit WETH the portfolio is price-exposed to: the
        position's WETH side plus any WETH-denominated fees still
        uncollected (cash and the token0 fee portion carry no price
        exposure). This is what benchmark_relative's reward nets out."""
        return self._position_weth_amount() + self.unclaimed_fee_amount1

    def _hedge_price_pnl_usd(self, prev_exposure_weth: float, price_change_usd: float) -> float:
        """Mark-to-market P&L of a short perp sized to prev_exposure_weth WETH."""
        return -prev_exposure_weth * price_change_usd

    def _hedge_funding_usd(self, prev_exposure_weth: float, price_now: float) -> float:
        """Funding settlement for the step; positive = income to the short
        (the common case: a positive funding rate means longs pay shorts)."""
        return prev_exposure_weth * price_now * self._funding_rate_for_step()

    def _accrue_fees(self) -> None:
        if self.position_tick_lower is None:
            return
        f0, f1 = self.engine.fee_growth_inside(self.position_tick_lower, self.position_tick_upper)
        start0, start1 = self.fee_checkpoint
        delta0 = (f0 - start0) % (2**256)
        delta1 = (f1 - start1) % (2**256)
        self.unclaimed_fee_amount0 += self.position_liquidity * delta0 / 2**128 / 10**6
        self.unclaimed_fee_amount1 += self.position_liquidity * delta1 / 2**128 / 10**18
        self.fee_checkpoint = (f0, f1)

    def _close_position(self) -> None:
        if self.position_tick_lower is None:
            return
        self._accrue_fees()
        self.cash_usd += self._position_value_usd() + self.unclaimed_fees_usd
        self.unclaimed_fee_amount0 = 0.0
        self.unclaimed_fee_amount1 = 0.0
        self.engine.close_shadow_position(self.position_tick_lower, self.position_tick_upper)
        self.position_tick_lower = None
        self.position_tick_upper = None
        self.position_liquidity = 0.0

    def _open_position(self, tick_lower: int, tick_upper: int, prior_amount1_usd: float = 0.0) -> float:
        """prior_amount1_usd: USD value of the WETH side of whatever position
        (if any) was just closed to fund this one -- the swap cost is netted
        against it, so only the actual token0/token1 composition change is
        charged, not the full notional. Returns the swap cost charged (0.0 if
        no position was opened)."""
        # A real LP keeps some wallet ETH aside for future gas rather than
        # deploying 100% of capital into the position -- without this, cash_usd
        # hits exactly 0 and every subsequent gas-incurring action (collect,
        # rebalance, exit) becomes permanently unaffordable, deadlocking the position.
        price = self._current_price()
        investable_estimate = self.cash_usd * (1.0 - CASH_RESERVE_FRACTION)
        liquidity_estimate = _liquidity_for_budget(
            investable_estimate, self.engine.pool.sqrt_price_x96, tick_lower, tick_upper, price
        )
        if liquidity_estimate <= 0:
            # Degenerate range/price: opening would debit cash for a worthless
            # position, evaporating the capital. Stay in cash instead.
            return 0.0

        # Swap cost is estimated off the pre-swap-cost budget (single-pass,
        # not iterated to a fixed point -- the fee is a small fraction of
        # notional, so the resulting bias in the final liquidity is negligible).
        _, _, target_amount1 = position_value_usd(
            liquidity_estimate, self.engine.pool.sqrt_price_x96, tick_lower, tick_upper, price
        )
        swap_cost = self._swap_cost_usd(abs(target_amount1 * price - prior_amount1_usd))
        self.cash_usd -= swap_cost

        investable = self.cash_usd * (1.0 - CASH_RESERVE_FRACTION)
        liquidity = _liquidity_for_budget(
            investable, self.engine.pool.sqrt_price_x96, tick_lower, tick_upper, price
        )
        if liquidity <= 0:
            self.cash_usd += swap_cost  # undo: no position ended up opening after all
            return 0.0
        self.engine.open_shadow_position(tick_lower, tick_upper)
        self.position_tick_lower = tick_lower
        self.position_tick_upper = tick_upper
        self.position_liquidity = liquidity
        self.fee_checkpoint = self.engine.fee_growth_inside(tick_lower, tick_upper)
        self.cash_usd -= investable
        self.hours_since_rebalance = 0.0
        return swap_cost

    def _apply_action(self, action: Action) -> tuple[float, float]:
        base_fee = self._current_base_fee()
        price = self._current_price()
        components = gas_components_for_action(action)
        gas_cost = (
            action_gas_cost_usd(components, base_fee, price, DEFAULT_GAS_UNITS) * self.gas_multiplier
            if components
            else 0.0
        )

        if gas_cost > self.cash_usd:
            # Not enough liquid cash on hand to pay for this transaction --
            # on-chain this would simply revert, so treat it as a no-op
            # (HOLD) rather than letting cash go negative to pay for it.
            return 0.0, 0.0

        self.cash_usd -= gas_cost

        target = target_range_for_action(
            action, self.engine.pool.tick, self.position_tick_lower, self.position_tick_upper,
            width_scale=self.width_scale,
        )

        swap_cost = 0.0
        if action == Action.COLLECT:
            self._accrue_fees()
            self.cash_usd += self.unclaimed_fees_usd
            self.unclaimed_fee_amount0 = 0.0
            self.unclaimed_fee_amount1 = 0.0
        elif action == Action.HOLD:
            pass
        elif action == Action.EXIT_TO_CASH:
            prior_amount1_usd = self._position_amount1_usd()
            self._close_position()
            # No new position to net against: the whole WETH-denominated
            # side must be swapped into cash, which carries zero price exposure.
            swap_cost = self._swap_cost_usd(prior_amount1_usd)
            self.cash_usd -= swap_cost
        else:  # rebalance / shift
            prior_amount1_usd = self._position_amount1_usd()
            self._close_position()
            if target is not None:
                swap_cost = self._open_position(*target, prior_amount1_usd=prior_amount1_usd)

        return gas_cost, swap_cost

    def _build_obs(self) -> np.ndarray:
        inputs = ObservationInputs(
            current_tick=self.engine.pool.tick,
            price_at_episode_start_usd=self.price_at_episode_start,
            current_price_usd=self._current_price(),
            returns_24h=self.return_history[-self._vol_lookback_short_steps:],
            returns_7d=self.return_history[-self._vol_lookback_long_steps:],
            recent_volume_usd=sum(self.volume_history[-1:]) if self.volume_history else 0.0,
            volume_log_mean=self.market_stats.volume_log_mean,
            volume_log_std=self.market_stats.volume_log_std,
            position_tick_lower=self.position_tick_lower,
            position_tick_upper=self.position_tick_upper,
            unclaimed_fees_usd=self.unclaimed_fees_usd,
            initial_notional_usd=self.initial_notional_usd,
            hours_since_rebalance=self.hours_since_rebalance,
            episode_length_hours=self.episode_hours,
            gas_percentile=self.market_stats.gas_percentile(self._current_base_fee()),
        )
        return build_observation(self.engine, inputs)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        rng = self.np_random  # gymnasium's seeded Generator

        latest_start = self.end_ts - pd.Timedelta(hours=self.episode_hours)
        span_hours = max((latest_start - self.start_ts).total_seconds() / 3600, 0.0)
        offset_hours = float(rng.uniform(0, span_hours)) if span_hours > 0 else 0.0
        self.episode_start_ts = self.start_ts + pd.Timedelta(hours=offset_hours)
        self.episode_end_ts = self.episode_start_ts + pd.Timedelta(hours=self.episode_hours)

        snap_ts, snap_path = self.snapshot_index.nearest_at_or_before(self.episode_start_ts)
        self.engine = load_snapshot(snap_path)
        # Binary search over the (asserted-sorted) timestamp column instead
        # of an O(N) boolean mask -- millions of events x hundreds of steps
        # x n_envs made the mask the training bottleneck.
        lo = self.events_df["timestamp"].searchsorted(snap_ts, side="right")
        hi = self.events_df["timestamp"].searchsorted(self.episode_start_ts, side="right")
        for row in self.events_df.iloc[lo:hi].itertuples():
            _apply_row(self.engine, row)

        self.current_ts = self.episode_start_ts
        self.price_at_episode_start = self._current_price()
        self.prev_price = self.price_at_episode_start
        self.position_tick_lower = None
        self.position_tick_upper = None
        self.position_liquidity = 0.0
        self.unclaimed_fee_amount0 = 0.0
        self.unclaimed_fee_amount1 = 0.0
        self.cash_usd = self.initial_notional_usd
        self.hedge_margin_usd = 0.0
        self.hours_since_rebalance = 0.0
        self.return_history = []
        self.volume_history = []
        self.prev_portfolio_value = self._portfolio_value_usd()
        self.prev_weth_exposure = 0.0

        return self._build_obs(), {}

    def step(self, action):
        action = Action(action)
        step_end_ts = min(self.current_ts + pd.Timedelta(hours=self.step_hours), self.episode_end_ts)

        events_lo = self.events_df["timestamp"].searchsorted(self.current_ts, side="right")
        events_hi = self.events_df["timestamp"].searchsorted(step_end_ts, side="right")
        step_events = self.events_df.iloc[events_lo:events_hi]
        volume_usd = 0.0
        for row in step_events.itertuples():
            _apply_row(self.engine, row)
            if row.event_type == "Swap":
                price = human_price_usd_per_eth(int(row.sqrt_price_x96))
                zero_for_one = row.amount0 > 0
                amt = abs(row.amount0) / 10**6 if zero_for_one else abs(row.amount1) / 10**18 * price
                volume_usd += amt

        self.current_ts = step_end_ts
        self.hours_since_rebalance += self.step_hours

        self._accrue_fees()
        gas_cost, swap_cost = self._apply_action(action)

        price_now = self._current_price()
        price_change_usd = price_now - self.prev_price
        self.return_history.append(float(np.log(price_now / self.prev_price)))
        self.prev_price = price_now
        self.volume_history.append(volume_usd)

        hedge_pnl_usd = 0.0
        hedge_funding_usd = 0.0
        if self.hedge_enabled:
            hedge_price_pnl_usd = self._hedge_price_pnl_usd(self.prev_weth_exposure, price_change_usd)
            hedge_funding_usd = self._hedge_funding_usd(self.prev_weth_exposure, price_now)
            hedge_pnl_usd = hedge_price_pnl_usd + hedge_funding_usd
            self.hedge_margin_usd += hedge_pnl_usd

        portfolio_value = self._portfolio_value_usd()
        pnl_usd = portfolio_value - self.prev_portfolio_value
        if self.reward_mode == "benchmark_relative":
            # Subtract the P&L a passive holder of last step's token
            # composition would have made, so the reward is LP alpha
            # (fees - IL - gas) instead of being dominated by ETH beta: a
            # policy can no longer look good by merely being long WETH in an
            # up-market or in cash in a down-market. The benchmark uses the
            # start-of-step total WETH exposure -- position plus uncollected
            # WETH-denominated fees, both of which float with price
            # (composition drifts as price crosses the range within the
            # step; start-of-step is the same HODL convention as
            # il.impermanent_loss_usd).
            pnl_usd -= self.prev_weth_exposure * price_change_usd
        reward = pnl_usd / self.initial_notional_usd
        self.prev_portfolio_value = portfolio_value
        self.prev_weth_exposure = self._total_weth_exposure()

        truncated = self.current_ts >= self.episode_end_ts or self.current_ts >= self.data_end_ts
        terminated = False
        if self.position_tick_lower is None:
            range_lower_usd = range_upper_usd = None
        else:
            lo = human_price_usd_per_eth(sqrt_price_x96_from_tick(self.position_tick_lower))
            hi = human_price_usd_per_eth(sqrt_price_x96_from_tick(self.position_tick_upper))
            range_lower_usd, range_upper_usd = min(lo, hi), max(lo, hi)
        info = {
            "portfolio_value_usd": portfolio_value,
            "gas_cost_usd": gas_cost,
            "swap_cost_usd": swap_cost,
            "hedge_pnl_usd": hedge_pnl_usd,
            "hedge_funding_usd": hedge_funding_usd,
            "unclaimed_fees_usd": self.unclaimed_fees_usd,
            "in_range": self.position_tick_lower is not None
            and self.position_tick_lower <= self.engine.pool.tick < self.position_tick_upper,
            # Captured here (not read from live env attributes after step()
            # returns) because VecEnv wrappers auto-reset the underlying env
            # on the same call that reports truncated=True, so by the time a
            # caller inspects env.current_ts/env._current_price() on the
            # terminal step, they'd already reflect the *next* episode.
            "timestamp": self.current_ts,
            "price_usd": self._current_price(),
            "range_lower_usd": range_lower_usd,
            "range_upper_usd": range_upper_usd,
        }
        return self._build_obs(), reward, terminated, truncated, info
