"""Gymnasium environment for the Uniswap V3 concentrated-liquidity LP agent.

Portfolio accounting is deliberately simple: `portfolio_value_usd = cash_usd +
position_value_usd + unclaimed_fees_usd`. The per-step reward is just the
change in this single number (scaled by the initial notional) -- fees earned,
impermanent loss, and gas costs are all *already* reflected in it (fees raise
unclaimed_fees_usd, gas reduces cash_usd, IL shows up as the position's
mark-to-market moving differently than cash would have), so there's no need
to compute "fees - IL - gas" as three separate terms that could double-count.
"""
from typing import Optional

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces

from .actions import Action, N_ACTIONS, gas_components_for_action, target_range_for_action
from .fee_engine import FeeEngine
from .gas_model import DEFAULT_GAS_UNITS, action_gas_cost_usd
from .il import position_value_usd
from .observations import OBS_DIM, ObservationInputs, build_observation
from .snapshot import SnapshotIndex, apply_event, load_snapshot
from .tick_math import human_price_usd_per_eth, sqrt_price_x96_from_tick

Q96 = 2**96
CASH_RESERVE_FRACTION = 0.02  # kept aside as a gas buffer whenever a position is opened


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
    ):
        super().__init__()
        # Standardize on tz-aware UTC, ns precision: real (BigQuery-sourced) data is
        # tz-aware, synthetic/test data is often naive, and episode/step timestamps
        # involve fractional-hour arithmetic (random reset offsets) that naturally
        # produces ns-resolution Timestamps -- pandas won't silently truncate a
        # finer-resolution Timestamp, or compare tz-aware against tz-naive, so both
        # need to be forced into the same representation up front.
        self.events_df = events_df.assign(
            timestamp=pd.to_datetime(events_df["timestamp"], utc=True).dt.as_unit("ns")
        )
        self.gas_df = gas_df.assign(
            block_timestamp=pd.to_datetime(gas_df["block_timestamp"], utc=True).dt.as_unit("ns")
        )
        self.gas_df = self.gas_df.sort_values("block_timestamp").reset_index(drop=True)
        self.snapshot_index = snapshot_index
        self.start_ts = _to_utc_timestamp(start_ts)
        self.end_ts = _to_utc_timestamp(end_ts)
        # Real on-chain events never extend past this; an episode that runs
        # beyond it would silently replay a frozen market (no swaps, no fee
        # accrual) instead of ending, see step()'s truncation check below.
        self.data_end_ts = self.events_df["timestamp"].max()
        self.episode_hours = episode_hours
        self.step_hours = step_hours
        self.initial_notional_usd = initial_notional_usd
        self.market_stats = MarketStats(swaps_df, self.gas_df)

        self.action_space = spaces.Discrete(N_ACTIONS)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(OBS_DIM,), dtype=np.float32)

        self._np_random_local = np.random.default_rng()

        # episode-scoped state, set in reset()
        self.engine: Optional[FeeEngine] = None
        self.position_tick_lower = None
        self.position_tick_upper = None
        self.position_liquidity = 0.0
        self.fee_checkpoint = (0, 0)
        self.unclaimed_fees_usd = 0.0
        self.cash_usd = initial_notional_usd
        self.hours_since_rebalance = 0.0
        self.price_history: list = []
        self.volume_history: list = []
        self.current_ts = None
        self.episode_end_ts = None
        self.episode_start_ts = None
        self.price_at_episode_start = None
        self.prev_portfolio_value = None

    def _current_price(self) -> float:
        return human_price_usd_per_eth(self.engine.pool.sqrt_price_x96)

    def _current_base_fee(self) -> float:
        idx = self.gas_df["block_timestamp"].searchsorted(self.current_ts, side="right") - 1
        idx = max(0, min(idx, len(self.gas_df) - 1))
        return float(self.gas_df["base_fee_per_gas"].iloc[idx])

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

    def _portfolio_value_usd(self) -> float:
        return self.cash_usd + self._position_value_usd() + self.unclaimed_fees_usd

    def _accrue_fees(self) -> None:
        if self.position_tick_lower is None:
            return
        f0, f1 = self.engine.fee_growth_inside(self.position_tick_lower, self.position_tick_upper)
        start0, start1 = self.fee_checkpoint
        delta0 = (f0 - start0) % (2**256)
        delta1 = (f1 - start1) % (2**256)
        fees0 = self.position_liquidity * delta0 / 2**128 / 10**6
        fees1 = self.position_liquidity * delta1 / 2**128 / 10**18
        self.unclaimed_fees_usd += fees0 * 1.0 + fees1 * self._current_price()
        self.fee_checkpoint = (f0, f1)

    def _close_position(self) -> None:
        if self.position_tick_lower is None:
            return
        self._accrue_fees()
        self.cash_usd += self._position_value_usd() + self.unclaimed_fees_usd
        self.unclaimed_fees_usd = 0.0
        self.engine.close_shadow_position(self.position_tick_lower, self.position_tick_upper)
        self.position_tick_lower = None
        self.position_tick_upper = None
        self.position_liquidity = 0.0

    def _open_position(self, tick_lower: int, tick_upper: int) -> None:
        # A real LP keeps some wallet ETH aside for future gas rather than
        # deploying 100% of capital into the position -- without this, cash_usd
        # hits exactly 0 and every subsequent gas-incurring action (collect,
        # rebalance, exit) becomes permanently unaffordable, deadlocking the position.
        investable = self.cash_usd * (1.0 - CASH_RESERVE_FRACTION)
        liquidity = _liquidity_for_budget(
            investable, self.engine.pool.sqrt_price_x96, tick_lower, tick_upper, self._current_price()
        )
        self.engine.open_shadow_position(tick_lower, tick_upper)
        self.position_tick_lower = tick_lower
        self.position_tick_upper = tick_upper
        self.position_liquidity = liquidity
        self.fee_checkpoint = self.engine.fee_growth_inside(tick_lower, tick_upper)
        self.cash_usd -= investable
        self.hours_since_rebalance = 0.0

    def _apply_action(self, action: Action) -> float:
        base_fee = self._current_base_fee()
        price = self._current_price()
        components = gas_components_for_action(action)
        gas_cost = action_gas_cost_usd(components, base_fee, price, DEFAULT_GAS_UNITS) if components else 0.0

        if gas_cost > self.cash_usd:
            # Not enough liquid cash on hand to pay for this transaction --
            # on-chain this would simply revert, so treat it as a no-op
            # (HOLD) rather than letting cash go negative to pay for it.
            return 0.0

        self.cash_usd -= gas_cost

        target = target_range_for_action(action, self.engine.pool.tick, self.position_tick_lower, self.position_tick_upper)

        if action == Action.COLLECT:
            self._accrue_fees()
            self.cash_usd += self.unclaimed_fees_usd
            self.unclaimed_fees_usd = 0.0
        elif action == Action.HOLD:
            pass
        elif action == Action.EXIT_TO_CASH:
            self._close_position()
        else:  # rebalance / shift
            self._close_position()
            if target is not None:
                self._open_position(*target)

        return gas_cost

    def _build_obs(self) -> np.ndarray:
        inputs = ObservationInputs(
            current_tick=self.engine.pool.tick,
            price_at_episode_start_usd=self.price_at_episode_start,
            current_price_usd=self._current_price(),
            returns_24h=self.price_history[-24:],
            returns_7d=self.price_history[-168:],
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
        mask = (self.events_df["timestamp"] > snap_ts) & (self.events_df["timestamp"] <= self.episode_start_ts)
        for row in self.events_df[mask].itertuples():
            _apply_row(self.engine, row)

        self.current_ts = self.episode_start_ts
        self.price_at_episode_start = self._current_price()
        self.position_tick_lower = None
        self.position_tick_upper = None
        self.position_liquidity = 0.0
        self.unclaimed_fees_usd = 0.0
        self.cash_usd = self.initial_notional_usd
        self.hours_since_rebalance = 0.0
        self.price_history = []
        self.volume_history = []
        self.prev_portfolio_value = self._portfolio_value_usd()

        return self._build_obs(), {}

    def step(self, action):
        action = Action(action)
        step_end_ts = min(self.current_ts + pd.Timedelta(hours=self.step_hours), self.episode_end_ts)

        mask = (self.events_df["timestamp"] > self.current_ts) & (self.events_df["timestamp"] <= step_end_ts)
        step_events = self.events_df[mask]
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
        gas_cost = self._apply_action(action)

        self.price_history.append(self._current_price())
        self.volume_history.append(volume_usd)

        portfolio_value = self._portfolio_value_usd()
        reward = (portfolio_value - self.prev_portfolio_value) / self.initial_notional_usd
        self.prev_portfolio_value = portfolio_value

        truncated = self.current_ts >= self.episode_end_ts or self.current_ts >= self.data_end_ts
        terminated = False
        info = {
            "portfolio_value_usd": portfolio_value,
            "gas_cost_usd": gas_cost,
            "unclaimed_fees_usd": self.unclaimed_fees_usd,
            "in_range": self.position_tick_lower is not None
            and self.position_tick_lower <= self.engine.pool.tick < self.position_tick_upper,
        }
        return self._build_obs(), reward, terminated, truncated, info
