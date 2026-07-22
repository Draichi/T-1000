import math

import pytest

from t1000 import tick_math
from t1000.tick_math import (
    amounts_for_liquidity,
    human_price_usd_per_eth,
    liquidity_for_amounts,
    price_from_tick,
    round_tick_to_spacing,
    sqrt_price_x96_from_tick,
    tick_from_sqrt_price_x96,
)


def test_tick_zero_gives_sqrt_price_q96():
    assert sqrt_price_x96_from_tick(0) == 2**96


def test_price_from_tick_zero_is_one():
    assert price_from_tick(0) == pytest.approx(1.0)


@pytest.mark.parametrize("tick", [-200000, -12345, -1, 0, 1, 12345, 200000])
def test_sqrt_price_tick_round_trip(tick):
    sqrt_p = sqrt_price_x96_from_tick(tick)
    recovered = tick_from_sqrt_price_x96(sqrt_p)
    # floor() in tick_from_sqrt_price_x96 can legitimately land one tick low
    # due to floating point representation of the boundary; never further off.
    assert abs(recovered - tick) <= 1


def test_round_tick_to_spacing():
    assert round_tick_to_spacing(23) == 20
    assert round_tick_to_spacing(-23) == -30  # floor division rounds toward -inf
    assert round_tick_to_spacing(20) == 20


def test_human_price_monotonically_decreases_with_tick():
    p_low = human_price_usd_per_eth(sqrt_price_x96_from_tick(190000))
    p_high = human_price_usd_per_eth(sqrt_price_x96_from_tick(200000))
    assert p_high < p_low


def test_human_price_realistic_order_of_magnitude():
    # tick ~200000 is in the historical range for the USDC/WETH 0.05% pool;
    # this only guards against decimal-conversion bugs (off by 10^n), not an
    # exact price assertion.
    usd_per_eth = human_price_usd_per_eth(sqrt_price_x96_from_tick(200000))
    assert 100 < usd_per_eth < 100_000


def test_amounts_for_liquidity_price_below_range_is_all_token0():
    amount0, amount1 = amounts_for_liquidity(1000.0, sqrt_price=1.0, sqrt_price_lower=2.0, sqrt_price_upper=3.0)
    assert amount1 == 0.0
    assert amount0 == pytest.approx(1000.0 * (1 / 2 - 1 / 3))


def test_amounts_for_liquidity_price_above_range_is_all_token1():
    amount0, amount1 = amounts_for_liquidity(1000.0, sqrt_price=4.0, sqrt_price_lower=2.0, sqrt_price_upper=3.0)
    assert amount0 == 0.0
    assert amount1 == pytest.approx(1000.0 * (3 - 2))


def test_amounts_for_liquidity_price_inside_range_has_both_tokens():
    amount0, amount1 = amounts_for_liquidity(1000.0, sqrt_price=2.5, sqrt_price_lower=2.0, sqrt_price_upper=3.0)
    assert amount0 == pytest.approx(1000.0 * (1 / 2.5 - 1 / 3))
    assert amount1 == pytest.approx(1000.0 * (2.5 - 2))
    assert amount0 > 0 and amount1 > 0


def test_liquidity_for_amounts_is_inverse_of_amounts_for_liquidity():
    liquidity = 1234.5
    sqrt_price, lower, upper = 2.5, 2.0, 3.0
    amount0, amount1 = amounts_for_liquidity(liquidity, sqrt_price, lower, upper)
    recovered = liquidity_for_amounts(amount0, amount1, sqrt_price, lower, upper)
    assert recovered == pytest.approx(liquidity)
