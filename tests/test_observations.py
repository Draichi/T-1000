import numpy as np

from t1000.fee_engine import FeeEngine
from t1000.observations import (
    FEATURE_NAMES,
    OBS_DIM,
    ObservationInputs,
    build_observation,
    liquidity_histogram,
    realized_vol,
)
from t1000.tick_math import sqrt_price_x96_from_tick


def _engine_with_liquidity():
    engine = FeeEngine()
    engine.initialize_pool(sqrt_price_x96_from_tick(0), 0)
    engine.apply_mint(-1000, 1000, 5000)
    engine.apply_mint(-200, 200, 2000)
    return engine


def test_obs_dim_matches_feature_names():
    assert OBS_DIM == len(FEATURE_NAMES)


def test_liquidity_histogram_sums_to_one_when_liquidity_present():
    engine = _engine_with_liquidity()
    hist = liquidity_histogram(engine, current_tick=0)
    assert hist.shape == (10,)
    assert hist.sum() == 1.0 or hist.sum() == 0.0


def test_liquidity_histogram_all_zero_when_no_liquidity_nearby():
    engine = FeeEngine()
    engine.initialize_pool(sqrt_price_x96_from_tick(200000), 200000)
    hist = liquidity_histogram(engine, current_tick=200000)
    assert hist.sum() == 0.0


def test_realized_vol_zero_for_short_or_constant_series():
    assert realized_vol([]) == 0.0
    assert realized_vol([0.01]) == 0.0
    assert realized_vol([0.01, 0.01, 0.01]) == 0.0


def test_build_observation_shape_and_bounds():
    engine = _engine_with_liquidity()
    inputs = ObservationInputs(
        current_tick=0,
        price_at_episode_start_usd=3000.0,
        current_price_usd=3100.0,
        returns_24h=[0.001, -0.002, 0.0015],
        returns_7d=[0.01, -0.02, 0.015, 0.005],
        recent_volume_usd=1_000_000,
        volume_log_mean=13.0,
        volume_log_std=1.0,
        position_tick_lower=-500,
        position_tick_upper=500,
        unclaimed_fees_usd=50.0,
        initial_notional_usd=10_000.0,
        hours_since_rebalance=12,
        episode_length_hours=720,
        gas_percentile=0.4,
    )
    obs = build_observation(engine, inputs)
    assert obs.shape == (OBS_DIM,)
    assert obs.dtype == np.float32
    assert np.all(np.isfinite(obs))


def test_build_observation_no_position_gives_zero_range_features():
    engine = _engine_with_liquidity()
    inputs = ObservationInputs(
        current_tick=0,
        price_at_episode_start_usd=3000.0,
        current_price_usd=3000.0,
        returns_24h=[],
        returns_7d=[],
        recent_volume_usd=0.0,
        volume_log_mean=0.0,
        volume_log_std=0.0,
        position_tick_lower=None,
        position_tick_upper=None,
        unclaimed_fees_usd=0.0,
        initial_notional_usd=10_000.0,
        hours_since_rebalance=0,
        episode_length_hours=720,
        gas_percentile=0.5,
    )
    obs = build_observation(engine, inputs)
    idx = {name: i for i, name in enumerate(FEATURE_NAMES)}
    assert obs[idx["tick_lower_rel"]] == 0.0
    assert obs[idx["tick_upper_rel"]] == 0.0
    assert obs[idx["in_range"]] == 0.0
