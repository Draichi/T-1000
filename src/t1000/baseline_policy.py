"""Deterministic full-range/fixed-width baseline LP policy: opens (or
re-centers) a wide fixed range whenever it has no position or has drifted
out of range, and otherwise just collects fees on a fixed cadence. Exposes
the same `.predict(obs, deterministic=True)` interface SB3 models do, so
backtest.py can swap it in for a trained policy with no other changes.

Reads position/range state entirely from the observation vector (rather than
reaching into env internals), so it's a fair, self-contained comparison
running through the exact same env mechanics as the trained agent.
"""
import numpy as np

from .actions import Action
from .observations import FEATURE_NAMES

_IDX = {name: i for i, name in enumerate(FEATURE_NAMES)}
_DEFAULT_COLLECT_INTERVAL_FRAC = 168 / 720  # weekly, assuming a 30-day/720h episode


class FullRangeBaselinePolicy:
    def __init__(
        self,
        rebalance_action: Action = Action.REBALANCE_WIDE,
        collect_interval_frac: float = _DEFAULT_COLLECT_INTERVAL_FRAC,
    ):
        self.rebalance_action = rebalance_action
        self.collect_interval_frac = collect_interval_frac

    def predict(self, observation, state=None, episode_start=None, deterministic=True):
        obs = np.asarray(observation)
        batched = obs.ndim == 2
        if not batched:
            obs = obs[None, :]

        actions = np.zeros(obs.shape[0], dtype=np.int64)
        for i, row in enumerate(obs):
            in_range = row[_IDX["in_range"]]
            tick_lower_rel = row[_IDX["tick_lower_rel"]]
            tick_upper_rel = row[_IDX["tick_upper_rel"]]
            time_frac = row[_IDX["time_since_rebalance_frac"]]
            has_position = not (tick_lower_rel == 0.0 and tick_upper_rel == 0.0 and in_range == 0.0)

            if not has_position or in_range == 0.0:
                actions[i] = int(self.rebalance_action)
            elif time_frac >= self.collect_interval_frac:
                actions[i] = int(Action.COLLECT)
            else:
                actions[i] = int(Action.HOLD)

        if not batched:
            return actions[0], state
        return actions, state
