"""Builds the flat observation vector for UniswapV3LPEnv from engine state,
recent market history, and the agent's current position."""
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .fee_engine import FeeEngine
from .tick_math import tick_delta_for_price_pct

N_LIQUIDITY_BUCKETS = 10
LIQUIDITY_BUCKET_PRICE_RANGE_PCT = 0.05

FEATURE_NAMES = [
    "log_price_rel_to_episode_start",
    "volatility_24h",
    "volatility_7d",
    "volume_zscore",
    *[f"liquidity_bucket_{i}" for i in range(N_LIQUIDITY_BUCKETS)],
    "tick_lower_rel",
    "tick_upper_rel",
    "in_range",
    "unclaimed_fees_scaled",
    "time_since_rebalance_frac",
    "gas_percentile",
]
OBS_DIM = len(FEATURE_NAMES)

# Scale constants for squashing realized volatility (stdev of log returns)
# into roughly [0, 1]; these are rough priors, not calibrated against the
# actual historical distribution -- fine for a PoC, worth revisiting later.
VOL_24H_SCALE = 0.05
VOL_7D_SCALE = 0.10
TICK_RANGE_REL_SCALE = 10_000


def liquidity_histogram(
    engine: FeeEngine,
    current_tick: int,
    n_buckets: int = N_LIQUIDITY_BUCKETS,
    price_range_pct: float = LIQUIDITY_BUCKET_PRICE_RANGE_PCT,
) -> np.ndarray:
    """Fraction of nearby (gross) liquidity sitting in each of n_buckets
    equal-width tick buckets spanning +/-price_range_pct around current_tick."""
    delta = tick_delta_for_price_pct(price_range_pct)
    lo, hi = current_tick - delta, current_tick + delta
    bucket_width = max(1, (hi - lo) // n_buckets)
    buckets = np.zeros(n_buckets, dtype=np.float64)
    for tick, info in engine.tick_map.items():
        if lo <= tick < hi and info.liquidity_gross > 0:
            idx = min(n_buckets - 1, int((tick - lo) // bucket_width))
            buckets[idx] += info.liquidity_gross
    total = buckets.sum()
    if total > 0:
        buckets = buckets / total
    return buckets


def realized_vol(log_returns: list) -> float:
    if len(log_returns) < 2:
        return 0.0
    return float(np.std(log_returns))


@dataclass
class ObservationInputs:
    current_tick: int
    price_at_episode_start_usd: float
    current_price_usd: float
    returns_24h: list
    returns_7d: list
    recent_volume_usd: float
    volume_log_mean: float
    volume_log_std: float
    position_tick_lower: Optional[int]
    position_tick_upper: Optional[int]
    unclaimed_fees_usd: float
    initial_notional_usd: float
    hours_since_rebalance: float
    episode_length_hours: float
    gas_percentile: float  # 0..1, precomputed by the caller from historical base_fee_per_gas


def build_observation(engine: FeeEngine, inputs: ObservationInputs) -> np.ndarray:
    log_price_rel = float(
        np.clip(np.log(inputs.current_price_usd / inputs.price_at_episode_start_usd), -1, 1)
    )
    vol_24h = float(np.clip(realized_vol(inputs.returns_24h) / VOL_24H_SCALE, 0, 1))
    vol_7d = float(np.clip(realized_vol(inputs.returns_7d) / VOL_7D_SCALE, 0, 1))

    if inputs.volume_log_std > 0:
        z = (np.log1p(max(inputs.recent_volume_usd, 0.0)) - inputs.volume_log_mean) / inputs.volume_log_std
        volume_z = float(np.clip(z, -3, 3) / 3)
    else:
        volume_z = 0.0

    buckets = liquidity_histogram(engine, inputs.current_tick)

    has_position = inputs.position_tick_lower is not None
    if has_position:
        tick_lower_rel = float(
            np.clip((inputs.position_tick_lower - inputs.current_tick) / TICK_RANGE_REL_SCALE, -1, 1)
        )
        tick_upper_rel = float(
            np.clip((inputs.position_tick_upper - inputs.current_tick) / TICK_RANGE_REL_SCALE, -1, 1)
        )
        in_range = 1.0 if inputs.position_tick_lower <= inputs.current_tick < inputs.position_tick_upper else 0.0
    else:
        tick_lower_rel = 0.0
        tick_upper_rel = 0.0
        in_range = 0.0

    notional_log = max(np.log1p(inputs.initial_notional_usd), 1e-6)
    fees_scaled = float(np.clip(np.log1p(max(inputs.unclaimed_fees_usd, 0.0)) / notional_log, 0, 2) / 2)

    time_frac = float(np.clip(inputs.hours_since_rebalance / max(inputs.episode_length_hours, 1e-6), 0, 1))
    gas_pct = float(np.clip(inputs.gas_percentile, 0, 1))

    features = np.concatenate(
        [
            [log_price_rel, vol_24h, vol_7d, volume_z],
            buckets,
            [tick_lower_rel, tick_upper_rel, in_range, fees_scaled, time_frac, gas_pct],
        ]
    ).astype(np.float32)

    assert features.shape[0] == OBS_DIM
    return features
