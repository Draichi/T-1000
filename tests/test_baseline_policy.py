import numpy as np

from t1000.actions import Action
from t1000.baseline_policy import FullRangeBaselinePolicy
from t1000.observations import FEATURE_NAMES

_IDX = {name: i for i, name in enumerate(FEATURE_NAMES)}


def _make_obs(**overrides):
    obs = np.zeros(len(FEATURE_NAMES), dtype=np.float32)
    for key, value in overrides.items():
        obs[_IDX[key]] = value
    return obs


def test_no_position_triggers_rebalance():
    policy = FullRangeBaselinePolicy()
    obs = _make_obs()  # tick_lower_rel=0, tick_upper_rel=0, in_range=0 => no position
    action, _ = policy.predict(obs)
    assert action == int(policy.rebalance_action)


def test_out_of_range_triggers_rebalance():
    policy = FullRangeBaselinePolicy()
    obs = _make_obs(tick_lower_rel=-0.5, tick_upper_rel=-0.1, in_range=0.0)
    action, _ = policy.predict(obs)
    assert action == int(policy.rebalance_action)


def test_in_range_before_collect_interval_holds():
    policy = FullRangeBaselinePolicy()
    obs = _make_obs(tick_lower_rel=-0.1, tick_upper_rel=0.1, in_range=1.0, time_since_rebalance_frac=0.05)
    action, _ = policy.predict(obs)
    assert action == int(Action.HOLD)


def test_in_range_past_collect_interval_collects():
    policy = FullRangeBaselinePolicy(collect_interval_frac=0.2)
    obs = _make_obs(tick_lower_rel=-0.1, tick_upper_rel=0.1, in_range=1.0, time_since_rebalance_frac=0.25)
    action, _ = policy.predict(obs)
    assert action == int(Action.COLLECT)


def test_predict_supports_batched_observations():
    policy = FullRangeBaselinePolicy()
    obs_no_pos = _make_obs()
    obs_in_range = _make_obs(tick_lower_rel=-0.1, tick_upper_rel=0.1, in_range=1.0, time_since_rebalance_frac=0.0)
    batch = np.stack([obs_no_pos, obs_in_range])
    actions, _ = policy.predict(batch)
    assert actions.shape == (2,)
    assert actions[0] == int(policy.rebalance_action)
    assert actions[1] == int(Action.HOLD)
