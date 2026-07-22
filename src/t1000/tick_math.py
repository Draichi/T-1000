"""Uniswap V3 tick <-> price <-> sqrtPriceX96 math, and the LiquidityAmounts
formulas for converting a position's liquidity into token amounts.

These mirror the on-chain `TickMath.sol` / `LiquidityAmounts.sol` libraries.
"""
import math

from . import constants

Q96 = 2**96


def price_from_tick(tick: int) -> float:
    """Raw price = token1 per token0, in the smallest-unit ratio (no decimals
    adjustment)."""
    return 1.0001**tick


def sqrt_price_x96_from_tick(tick: int) -> int:
    return round(math.sqrt(price_from_tick(tick)) * Q96)


def tick_from_sqrt_price_x96(sqrt_price_x96: int) -> int:
    ratio = (sqrt_price_x96 / Q96) ** 2
    return math.floor(math.log(ratio, 1.0001))


def human_price_usd_per_eth(sqrt_price_x96: int) -> float:
    """token0=USDC (6 decimals), token1=WETH (18 decimals) -> USD per ETH."""
    raw_price = (sqrt_price_x96 / Q96) ** 2  # WETH_wei per USDC_unit
    weth_per_usdc = raw_price * 10 ** (constants.TOKEN0_DECIMALS - constants.TOKEN1_DECIMALS)
    return 1.0 / weth_per_usdc


def round_tick_to_spacing(tick: int, spacing: int = constants.TICK_SPACING) -> int:
    return (tick // spacing) * spacing


def tick_delta_for_price_pct(pct: float) -> int:
    """Number of ticks spanning a +/-pct price move: tick = ln(1+pct)/ln(1.0001)."""
    return round(math.log(1 + pct) / math.log(1.0001))


def amounts_for_liquidity(
    liquidity: float, sqrt_price: float, sqrt_price_lower: float, sqrt_price_upper: float
) -> tuple[float, float]:
    """LiquidityAmounts.getAmountsForLiquidity, operating on raw (non-X96) sqrt
    prices for numerical simplicity in Python (float, not the exact on-chain
    fixed-point path) -- fine for simulation/backtesting, not for reproducing
    exact wei-level on-chain rounding.
    """
    if sqrt_price_lower > sqrt_price_upper:
        sqrt_price_lower, sqrt_price_upper = sqrt_price_upper, sqrt_price_lower

    if sqrt_price <= sqrt_price_lower:
        amount0 = liquidity * (1 / sqrt_price_lower - 1 / sqrt_price_upper)
        amount1 = 0.0
    elif sqrt_price >= sqrt_price_upper:
        amount0 = 0.0
        amount1 = liquidity * (sqrt_price_upper - sqrt_price_lower)
    else:
        amount0 = liquidity * (1 / sqrt_price - 1 / sqrt_price_upper)
        amount1 = liquidity * (sqrt_price - sqrt_price_lower)
    return amount0, amount1


def segment_token_deltas(liquidity: float, sqrt_price_start: float, sqrt_price_end: float) -> tuple[float, float]:
    """Change in pool reserves (token0, token1) as the active-liquidity price
    curve moves from sqrt_price_start to sqrt_price_end at constant
    liquidity, with NO tick crossing in between (single segment of a swap).
    Positive amount0 means token0 flowed into the pool (price fell); positive
    amount1 means token1 flowed in (price rose). Matches Uniswap's
    SwapMath.computeSwapStep curve-movement formulas.
    """
    amount0 = liquidity * (1 / sqrt_price_end - 1 / sqrt_price_start)
    amount1 = liquidity * (sqrt_price_end - sqrt_price_start)
    return amount0, amount1


def liquidity_for_amounts(
    amount0: float, amount1: float, sqrt_price: float, sqrt_price_lower: float, sqrt_price_upper: float
) -> float:
    """Inverse of amounts_for_liquidity: how much liquidity a given pair of
    token amounts supports over a range, at the current price."""
    if sqrt_price_lower > sqrt_price_upper:
        sqrt_price_lower, sqrt_price_upper = sqrt_price_upper, sqrt_price_lower

    if sqrt_price <= sqrt_price_lower:
        return amount0 / (1 / sqrt_price_lower - 1 / sqrt_price_upper)
    elif sqrt_price >= sqrt_price_upper:
        return amount1 / (sqrt_price_upper - sqrt_price_lower)
    else:
        l0 = amount0 / (1 / sqrt_price - 1 / sqrt_price_upper)
        l1 = amount1 / (sqrt_price - sqrt_price_lower)
        return min(l0, l1)
