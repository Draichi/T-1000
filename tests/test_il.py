import math

import pytest

from t1000 import constants
from t1000.il import impermanent_loss_usd, position_value_usd
from t1000.tick_math import human_price_usd_per_eth, price_from_tick, sqrt_price_x96_from_tick


def test_il_is_zero_when_price_unchanged():
    sqrt_p = sqrt_price_x96_from_tick(200000)
    usd_per_eth = human_price_usd_per_eth(sqrt_p)
    il = impermanent_loss_usd(
        liquidity=1_000_000,
        tick_lower=190000,
        tick_upper=210000,
        sqrt_price_x96_mint=sqrt_p,
        sqrt_price_x96_now=sqrt_p,
        usd_per_eth_now=usd_per_eth,
    )
    assert il == pytest.approx(0.0, abs=1e-6)


def test_il_is_nonpositive_when_price_moves_within_range():
    sqrt_p_mint = sqrt_price_x96_from_tick(200000)
    sqrt_p_now = sqrt_price_x96_from_tick(205000)
    usd_per_eth_now = human_price_usd_per_eth(sqrt_p_now)
    il = impermanent_loss_usd(
        liquidity=1_000_000,
        tick_lower=190000,
        tick_upper=210000,
        sqrt_price_x96_mint=sqrt_p_mint,
        sqrt_price_x96_now=sqrt_p_now,
        usd_per_eth_now=usd_per_eth_now,
    )
    assert il <= 1e-6  # fundamental AMM property: LP value <= HODL value after any price move


def test_full_range_il_matches_classic_closed_form():
    """Cross-check against the textbook full-range IL formula
    value_LP/value_HODL = 2*sqrt(r)/(1+r), where r = price_now/price_mint
    (raw token1-per-token0 ratio). Uses MIN_TICK/MAX_TICK as a finite stand-in
    for a truly infinite full range."""
    tick_lower, tick_upper = constants.MIN_TICK, constants.MAX_TICK
    tick_mint = 0
    tick_now = 5000

    sqrt_p_mint = sqrt_price_x96_from_tick(tick_mint)
    sqrt_p_now = sqrt_price_x96_from_tick(tick_now)
    usd_per_eth_now = human_price_usd_per_eth(sqrt_p_now)

    liquidity = 1_000_000_000.0
    value_now, _, _ = position_value_usd(liquidity, sqrt_p_now, tick_lower, tick_upper, usd_per_eth_now)
    _, amount0_mint_h, amount1_mint_h = position_value_usd(
        liquidity, sqrt_p_mint, tick_lower, tick_upper, usd_per_eth_now
    )
    value_hodl = amount0_mint_h * 1.0 + amount1_mint_h * usd_per_eth_now

    r = price_from_tick(tick_now) / price_from_tick(tick_mint)
    expected_ratio = 2 * math.sqrt(r) / (1 + r)

    assert value_now / value_hodl == pytest.approx(expected_ratio, rel=1e-6)
