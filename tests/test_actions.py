import pytest

from t1000 import constants
from t1000.actions import Action, gas_components_for_action, target_range_for_action


def test_hold_and_collect_keep_existing_range():
    for action in (Action.HOLD, Action.COLLECT):
        result = target_range_for_action(action, current_tick=100, position_tick_lower=-500, position_tick_upper=500)
        assert result == (-500, 500)


def test_hold_and_collect_with_no_position_return_none():
    for action in (Action.HOLD, Action.COLLECT):
        result = target_range_for_action(action, current_tick=100, position_tick_lower=None, position_tick_upper=None)
        assert result is None


def test_exit_to_cash_returns_none():
    result = target_range_for_action(Action.EXIT_TO_CASH, current_tick=100, position_tick_lower=-500, position_tick_upper=500)
    assert result is None


@pytest.mark.parametrize("action", [Action.REBALANCE_NARROW, Action.REBALANCE_MEDIUM, Action.REBALANCE_WIDE])
def test_rebalance_actions_center_on_current_tick_and_widen_with_size(action):
    lower, upper = target_range_for_action(action, current_tick=200000, position_tick_lower=None, position_tick_upper=None)
    assert lower < 200000 < upper
    assert lower % constants.TICK_SPACING == 0
    assert upper % constants.TICK_SPACING == 0


def test_wider_rebalance_gives_wider_range():
    narrow = target_range_for_action(Action.REBALANCE_NARROW, 200000, None, None)
    medium = target_range_for_action(Action.REBALANCE_MEDIUM, 200000, None, None)
    wide = target_range_for_action(Action.REBALANCE_WIDE, 200000, None, None)
    width_narrow = narrow[1] - narrow[0]
    width_medium = medium[1] - medium[0]
    width_wide = wide[1] - wide[0]
    assert width_narrow < width_medium < width_wide


def test_shift_up_moves_range_above_current_tick():
    lower, upper = target_range_for_action(Action.SHIFT_UP, current_tick=0, position_tick_lower=-1000, position_tick_upper=1000)
    assert lower > -1000  # shifted up relative to the old range
    assert upper - lower == pytest.approx(2000, abs=constants.TICK_SPACING * 2)


def test_shift_down_moves_range_below_current_tick():
    lower, upper = target_range_for_action(Action.SHIFT_DOWN, current_tick=0, position_tick_lower=-1000, position_tick_upper=1000)
    assert upper < 1000  # shifted down relative to the old range


def test_shift_with_no_existing_position_uses_default_width():
    lower, upper = target_range_for_action(Action.SHIFT_UP, current_tick=200000, position_tick_lower=None, position_tick_upper=None)
    assert lower < upper


def test_ticks_stay_within_min_max_bounds_near_extremes():
    lower, upper = target_range_for_action(Action.REBALANCE_WIDE, current_tick=constants.MAX_TICK - 5, position_tick_lower=None, position_tick_upper=None)
    assert constants.MIN_TICK <= lower < upper <= constants.MAX_TICK


def test_gas_components_hold_is_free_and_others_are_not():
    assert gas_components_for_action(Action.HOLD) == []
    assert "collect" in gas_components_for_action(Action.COLLECT)
    for action in (Action.REBALANCE_NARROW, Action.REBALANCE_MEDIUM, Action.REBALANCE_WIDE, Action.SHIFT_UP, Action.SHIFT_DOWN):
        components = gas_components_for_action(action)
        assert "mint" in components and "burn" in components
    assert gas_components_for_action(Action.EXIT_TO_CASH) == ["burn", "collect"]
