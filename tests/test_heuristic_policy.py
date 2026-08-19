"""Tests for the parametrized rule-based policy family used by
scripts/heuristic_sweep.py.

The load-bearing one is test_reference_knobs_reproduce_full_range_baseline:
the grid sweep is only comparable to every published PPO result if one cell of
it is bit-for-bit the reference policy those results were scored against.
"""
import numpy as np
import pytest

from t1000.actions import Action
from t1000.baseline_policy import FullRangeBaselinePolicy
from t1000.heuristic_policy import HeuristicPolicy
from t1000.observations import FEATURE_NAMES, OBS_DIM

_IDX = {name: i for i, name in enumerate(FEATURE_NAMES)}
WEEKLY = 168 / 720


def _obs(in_range=1.0, tick_lower_rel=-0.01, tick_upper_rel=0.01, time_frac=0.0, gas_percentile=0.5):
    row = np.zeros(OBS_DIM, dtype=np.float32)
    row[_IDX["in_range"]] = in_range
    row[_IDX["tick_lower_rel"]] = tick_lower_rel
    row[_IDX["tick_upper_rel"]] = tick_upper_rel
    row[_IDX["time_since_rebalance_frac"]] = time_frac
    row[_IDX["gas_percentile"]] = gas_percentile
    return row


def _no_position_obs():
    return _obs(in_range=0.0, tick_lower_rel=0.0, tick_upper_rel=0.0)


def test_reference_knobs_reproduce_full_range_baseline():
    """patience=0 + weekly collect + no gas gate == FullRangeBaselinePolicy."""
    reference = FullRangeBaselinePolicy()
    heuristic = HeuristicPolicy(
        rebalance_action=Action.REBALANCE_WIDE,
        out_of_range_patience=0,
        collect_interval_frac=WEEKLY,
        max_gas_percentile=1.0,
    )
    rng = np.random.default_rng(0)
    for _ in range(200):
        obs = rng.choice([_obs, _no_position_obs])()
        obs[_IDX["in_range"]] = float(rng.integers(0, 2))
        obs[_IDX["time_since_rebalance_frac"]] = float(rng.random())
        obs[_IDX["gas_percentile"]] = float(rng.random())
        expected, _ = reference.predict(obs, deterministic=True)
        got, _ = heuristic.predict(obs, deterministic=True)
        assert int(got) == int(expected), f"diverged on {obs[_IDX['in_range']]=}"


def test_no_position_always_rebalances_regardless_of_patience():
    """Patience is hysteresis on *leaving* a range, not a reason to sit in cash:
    with no position there is nothing to be patient about."""
    policy = HeuristicPolicy(out_of_range_patience=24)
    action, _ = policy.predict(_no_position_obs(), deterministic=True)
    assert int(action) == int(policy.rebalance_action)


def test_patience_defers_rebalance_until_threshold():
    policy = HeuristicPolicy(rebalance_action=Action.REBALANCE_MEDIUM, out_of_range_patience=3)
    obs = _obs(in_range=0.0)
    for step in range(3):
        action, _ = policy.predict(obs, deterministic=True)
        assert int(action) == int(Action.HOLD), f"rebalanced too early at step {step}"
    action, _ = policy.predict(obs, deterministic=True)
    assert int(action) == int(Action.REBALANCE_MEDIUM)


def test_out_of_range_counter_resets_on_reentry():
    """Price dipping out and back in must not accumulate toward the threshold --
    otherwise patience degenerates into a slow unconditional rebalance."""
    policy = HeuristicPolicy(out_of_range_patience=3)
    for _ in range(3):
        policy.predict(_obs(in_range=0.0), deterministic=True)
        policy.predict(_obs(in_range=1.0), deterministic=True)
    action, _ = policy.predict(_obs(in_range=0.0), deterministic=True)
    assert int(action) == int(Action.HOLD)


def test_reset_clears_episode_state():
    policy = HeuristicPolicy(out_of_range_patience=2)
    policy.predict(_obs(in_range=0.0), deterministic=True)
    policy.predict(_obs(in_range=0.0), deterministic=True)
    policy.reset()
    action, _ = policy.predict(_obs(in_range=0.0), deterministic=True)
    assert int(action) == int(Action.HOLD)


def test_collect_disabled_never_collects():
    policy = HeuristicPolicy(collect_interval_frac=None)
    action, _ = policy.predict(_obs(in_range=1.0, time_frac=0.99), deterministic=True)
    assert int(action) == int(Action.HOLD)


def test_collect_fires_at_interval():
    policy = HeuristicPolicy(collect_interval_frac=WEEKLY)
    action, _ = policy.predict(_obs(in_range=1.0, time_frac=WEEKLY + 1e-6), deterministic=True)
    assert int(action) == int(Action.COLLECT)


def test_gas_gate_defers_rebalance_when_gas_is_expensive():
    policy = HeuristicPolicy(out_of_range_patience=0, max_gas_percentile=0.5)
    expensive, _ = policy.predict(_obs(in_range=0.0, gas_percentile=0.9), deterministic=True)
    assert int(expensive) == int(Action.HOLD)
    policy.reset()
    cheap, _ = policy.predict(_obs(in_range=0.0, gas_percentile=0.1), deterministic=True)
    assert int(cheap) == int(policy.rebalance_action)


def test_batched_multi_row_rejected():
    """The out-of-range counter is per-episode state; sharing it across parallel
    envs would be silently wrong, so it must fail loudly instead."""
    policy = HeuristicPolicy()
    with pytest.raises(ValueError):
        policy.predict(np.stack([_obs(), _obs()]), deterministic=True)
