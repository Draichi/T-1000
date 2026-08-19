"""Parametrized rule-based LP policies, for the zero-training sanity check
described in TODO.md ("does anything beat doing nothing?").

`FullRangeBaselinePolicy` is already one point in this family (WIDE band,
zero patience, weekly collect) -- it is the reference every PPO variant has
been scored against. This module generalizes it along the three knobs a
rule-based LP actually has, so a grid sweep can answer whether the reference
point is near-optimal or merely arbitrary:

- `rebalance_action`  : band width (NARROW +/-2%, MEDIUM +/-5%, WIDE +/-10%)
- `out_of_range_patience` : steps to stay out of range before re-centering,
  i.e. hysteresis against whipsaw (each rebalance pays burn+collect+mint gas
  plus a swap cost, so reacting instantly is not free)
- `collect_interval_frac` : how often to COLLECT while in range; collecting
  crystallizes the WETH-denominated fee half into cash, which changes price
  exposure, so cadence is a real decision and not just gas bookkeeping

Same `.predict(obs, deterministic=True)` interface SB3 models expose, so
scripts/backtest.py-style runners can swap it in unchanged. Unlike the SB3
models it carries per-episode state (the out-of-range counter), so runners
must call `reset()` after each `env.reset()`.

Reads everything from the observation vector, never from env internals, so
the comparison runs through the exact same env mechanics as a trained agent.
"""
from typing import Optional

import numpy as np

from .actions import Action
from .observations import FEATURE_NAMES

_IDX = {name: i for i, name in enumerate(FEATURE_NAMES)}
_DEFAULT_COLLECT_INTERVAL_FRAC = 168 / 720  # weekly, assuming a 30-day/720h episode


class HeuristicPolicy:
    def __init__(
        self,
        rebalance_action: Action = Action.REBALANCE_WIDE,
        out_of_range_patience: int = 0,
        collect_interval_frac: Optional[float] = _DEFAULT_COLLECT_INTERVAL_FRAC,
        max_gas_percentile: float = 1.0,
        name: Optional[str] = None,
    ):
        """collect_interval_frac=None disables periodic COLLECT entirely (fees
        are then only swept by the burn+collect a rebalance already pays for).
        max_gas_percentile=1.0 disables the gas gate; below 1.0, a rebalance is
        deferred while gas sits above that percentile of the historical
        distribution."""
        self.rebalance_action = rebalance_action
        self.out_of_range_patience = out_of_range_patience
        self.collect_interval_frac = collect_interval_frac
        self.max_gas_percentile = max_gas_percentile
        self.name = name or (
            f"{rebalance_action.name.lower()}_p{out_of_range_patience}"
            f"_c{'none' if collect_interval_frac is None else round(collect_interval_frac, 3)}"
            f"_g{max_gas_percentile}"
        )
        self.reset()

    def reset(self) -> None:
        """Clears per-episode state. Runners must call this after env.reset()."""
        self._steps_out_of_range = 0

    def predict(self, observation, state=None, episode_start=None, deterministic=True):
        obs = np.asarray(observation)
        batched = obs.ndim == 2
        if batched:
            if obs.shape[0] != 1:
                # The out-of-range counter is per-episode state; a shared
                # counter across parallel envs would be silently wrong.
                raise ValueError("HeuristicPolicy is stateful and supports batch size 1 only")
            row = obs[0]
        else:
            row = obs

        in_range = row[_IDX["in_range"]]
        tick_lower_rel = row[_IDX["tick_lower_rel"]]
        tick_upper_rel = row[_IDX["tick_upper_rel"]]
        time_frac = row[_IDX["time_since_rebalance_frac"]]
        gas_percentile = row[_IDX["gas_percentile"]]
        has_position = not (tick_lower_rel == 0.0 and tick_upper_rel == 0.0 and in_range == 0.0)

        if has_position and in_range == 0.0:
            self._steps_out_of_range += 1
        else:
            self._steps_out_of_range = 0

        action = self._decide(
            has_position=has_position,
            in_range=bool(in_range),
            steps_out_of_range=self._steps_out_of_range,
            time_since_rebalance_frac=float(time_frac),
            gas_percentile=float(gas_percentile),
        )

        if action == self.rebalance_action or action in (
            Action.REBALANCE_NARROW,
            Action.REBALANCE_MEDIUM,
            Action.REBALANCE_WIDE,
        ):
            # A rebalance re-centers the band, so the counter restarts even if
            # the very next step is still (briefly) out of range.
            self._steps_out_of_range = 0

        result = np.int64(int(action))
        if batched:
            return np.array([result], dtype=np.int64), state
        return result, state

    def _decide(
        self,
        has_position: bool,
        in_range: bool,
        steps_out_of_range: int,
        time_since_rebalance_frac: float,
        gas_percentile: float,
    ) -> Action:
        """Returns the action for this step from the policy's knobs.

        With patience=0, collect_interval_frac=weekly and max_gas_percentile=1.0,
        this must reproduce FullRangeBaselinePolicy exactly -- that equivalence
        is asserted by tests/test_heuristic_policy.py and is what makes the grid
        sweep comparable to every published result.
        """
        # With no position there is no range to be patient about and no fees to
        # collect -- the only useful move is to mint one. Deliberately not gas-
        # gated: sitting in cash earns nothing at all, so deferring here costs
        # more than the gate could ever save.
        if not has_position:
            return self.rebalance_action

        if not in_range:
            # steps_out_of_range is already incremented for this step, so `>`
            # (not `>=`) makes patience=0 fire immediately -- the reference
            # baseline's behaviour -- and patience=N wait exactly N steps first.
            if steps_out_of_range > self.out_of_range_patience:
                # The gas gate defers, it does not cancel: the position stays out
                # of range and the counter keeps climbing, so the rebalance lands
                # on the first cheap step rather than never.
                if gas_percentile <= self.max_gas_percentile:
                    return self.rebalance_action
            # Out of range accrues no fees, so there is nothing worth paying
            # collect gas for -- wait instead.
            return Action.HOLD

        if self.collect_interval_frac is not None and time_since_rebalance_frac >= self.collect_interval_frac:
            return Action.COLLECT

        return Action.HOLD
