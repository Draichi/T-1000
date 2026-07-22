"""Impermanent loss for a concentrated liquidity position, via direct value
comparison (works for any range, including currently out-of-range positions
-- unlike the classic closed-form 2*sqrt(r)/(1+r)-1, which only applies to a
full-range position)."""
from . import constants
from .tick_math import amounts_for_liquidity, sqrt_price_x96_from_tick

Q96 = 2**96


def position_value_usd(
    liquidity: float, sqrt_price_x96_current: int, tick_lower: int, tick_upper: int, usd_per_eth: float
) -> tuple[float, float, float]:
    """Returns (value_usd, amount0_human, amount1_human)."""
    sqrt_p = sqrt_price_x96_current / Q96
    sqrt_lo = sqrt_price_x96_from_tick(tick_lower) / Q96
    sqrt_hi = sqrt_price_x96_from_tick(tick_upper) / Q96
    amount0_raw, amount1_raw = amounts_for_liquidity(liquidity, sqrt_p, sqrt_lo, sqrt_hi)
    amount0_human = amount0_raw / 10**constants.TOKEN0_DECIMALS
    amount1_human = amount1_raw / 10**constants.TOKEN1_DECIMALS
    value_usd = amount0_human * 1.0 + amount1_human * usd_per_eth
    return value_usd, amount0_human, amount1_human


def impermanent_loss_usd(
    liquidity: float,
    tick_lower: int,
    tick_upper: int,
    sqrt_price_x96_mint: int,
    sqrt_price_x96_now: int,
    usd_per_eth_now: float,
) -> float:
    """Negative = loss vs. having held the tokens minted at open time,
    valued at current prices."""
    value_now, _, _ = position_value_usd(liquidity, sqrt_price_x96_now, tick_lower, tick_upper, usd_per_eth_now)

    sqrt_p_mint = sqrt_price_x96_mint / Q96
    sqrt_lo = sqrt_price_x96_from_tick(tick_lower) / Q96
    sqrt_hi = sqrt_price_x96_from_tick(tick_upper) / Q96
    amount0_mint_raw, amount1_mint_raw = amounts_for_liquidity(liquidity, sqrt_p_mint, sqrt_lo, sqrt_hi)
    amount0_mint_human = amount0_mint_raw / 10**constants.TOKEN0_DECIMALS
    amount1_mint_human = amount1_mint_raw / 10**constants.TOKEN1_DECIMALS
    value_hodl = amount0_mint_human * 1.0 + amount1_mint_human * usd_per_eth_now

    return value_now - value_hodl
