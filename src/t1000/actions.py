"""Discrete(8) action space for the LP agent: maps an action to a target
(tick_lower, tick_upper) range (or "no position") plus the gas components it
incurs (see gas_model.py for the cost of each component)."""
import math
from enum import IntEnum
from typing import Optional

from . import constants
from .tick_math import round_tick_to_spacing

N_ACTIONS = 8


class Action(IntEnum):
    HOLD = 0
    COLLECT = 1
    REBALANCE_NARROW = 2   # +/-2% band around current tick
    REBALANCE_MEDIUM = 3   # +/-5%
    REBALANCE_WIDE = 4     # +/-10%
    SHIFT_UP = 5            # same width, recentered above current tick
    SHIFT_DOWN = 6          # same width, recentered below current tick
    EXIT_TO_CASH = 7        # burn + collect, hold no position until next rebalance


REBALANCE_WIDTH_PCT = {
    Action.REBALANCE_NARROW: 0.02,
    Action.REBALANCE_MEDIUM: 0.05,
    Action.REBALANCE_WIDE: 0.10,
}

GAS_COMPONENTS = {
    Action.HOLD: [],
    Action.COLLECT: ["collect"],
    Action.REBALANCE_NARROW: ["burn", "collect", "mint"],
    Action.REBALANCE_MEDIUM: ["burn", "collect", "mint"],
    Action.REBALANCE_WIDE: ["burn", "collect", "mint"],
    Action.SHIFT_UP: ["burn", "collect", "mint"],
    Action.SHIFT_DOWN: ["burn", "collect", "mint"],
    Action.EXIT_TO_CASH: ["burn", "collect"],
}


def _price_pct_to_tick_delta(pct: float) -> int:
    """Number of ticks spanning a +/-pct price move: tick = ln(1+pct)/ln(1.0001)."""
    return round(math.log(1 + pct) / math.log(1.0001))


def _clip_tick(tick: int) -> int:
    return max(constants.MIN_TICK, min(constants.MAX_TICK, tick))


def gas_components_for_action(action: Action) -> list[str]:
    return GAS_COMPONENTS[action]


def target_range_for_action(
    action: Action,
    current_tick: int,
    position_tick_lower: Optional[int],
    position_tick_upper: Optional[int],
) -> Optional[tuple[int, int]]:
    """Returns the (tick_lower, tick_upper) the action results in (rounded to
    TICK_SPACING), or None if the action results in no open position."""
    spacing = constants.TICK_SPACING

    if action in (Action.HOLD, Action.COLLECT):
        if position_tick_lower is None:
            return None
        return position_tick_lower, position_tick_upper

    if action == Action.EXIT_TO_CASH:
        return None

    if action in REBALANCE_WIDTH_PCT:
        delta = _price_pct_to_tick_delta(REBALANCE_WIDTH_PCT[action])
        lower = round_tick_to_spacing(_clip_tick(current_tick - delta), spacing)
        upper = round_tick_to_spacing(_clip_tick(current_tick + delta), spacing)
        if lower >= upper:
            upper = lower + spacing
        return lower, upper

    if action in (Action.SHIFT_UP, Action.SHIFT_DOWN):
        if position_tick_lower is None or position_tick_upper is None:
            delta = _price_pct_to_tick_delta(REBALANCE_WIDTH_PCT[Action.REBALANCE_MEDIUM])
            width = 2 * delta
        else:
            width = position_tick_upper - position_tick_lower
        half = max(width // 2, spacing)
        center = current_tick + half if action == Action.SHIFT_UP else current_tick - half
        lower = round_tick_to_spacing(_clip_tick(center - half), spacing)
        upper = round_tick_to_spacing(_clip_tick(center + half), spacing)
        if lower >= upper:
            upper = lower + spacing
        return lower, upper

    raise ValueError(f"Unhandled action: {action}")
