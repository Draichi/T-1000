"""Replay real Uniswap V3 pool events (Mint/Burn/Swap) to reconstruct
tick-level liquidity state and per-tick feeGrowthOutside, so that
feeGrowthInside can be computed for ANY tick range -- including a synthetic
range an RL agent chooses that was never a real historical position
("shadow ticks").

Design notes (see plan doc for full rationale):
- Swaps are REPLAYED from real on-chain (sqrtPriceX96, tick, liquidity)
  post-swap values -- we never simulate hypothetical price impact.
- A single swap may cross several initialized ticks; we walk each segment
  using the same closed-form curve math the contract uses.
- The agent's own liquidity is assumed negligible vs. real pool liquidity
  (no market-impact approximation, documented in the plan).
- Shadow ticks (liquidity_net=0) let us track feeGrowthOutside at the
  agent's chosen tick boundaries without perturbing real active liquidity.
"""
from dataclasses import dataclass, field

from . import constants
from .tick_math import segment_token_deltas, sqrt_price_x96_from_tick

Q128 = constants.Q128
Q256 = constants.Q256


@dataclass
class TickInfo:
    liquidity_net: int = 0
    liquidity_gross: int = 0
    fee_growth_outside0_x128: int = 0
    fee_growth_outside1_x128: int = 0
    shadow_refcount: int = 0


@dataclass
class PoolState:
    tick: int = 0
    sqrt_price_x96: int = 0
    liquidity: int = 0
    fee_growth_global0_x128: int = 0
    fee_growth_global1_x128: int = 0
    initialized: bool = False


class FeeEngine:
    """Deterministic replay engine. Feed events strictly in
    (block_number, log_index) order via apply_mint/apply_burn/apply_swap."""

    def __init__(self, fee_pips: int = constants.FEE_PIPS):
        self.fee_pips = fee_pips
        self.tick_map: dict[int, TickInfo] = {}
        self.pool = PoolState()
        self.liquidity_mismatches: list[tuple[int, int, int]] = []  # (tick, expected, actual)

    # -- tick bookkeeping -------------------------------------------------

    def _ensure_tick(self, tick: int) -> TickInfo:
        info = self.tick_map.get(tick)
        if info is None:
            info = TickInfo()
            if self.pool.tick >= tick:
                info.fee_growth_outside0_x128 = self.pool.fee_growth_global0_x128
                info.fee_growth_outside1_x128 = self.pool.fee_growth_global1_x128
            self.tick_map[tick] = info
        return info

    def _maybe_delete_tick(self, tick: int) -> None:
        info = self.tick_map.get(tick)
        if info is not None and info.liquidity_gross <= 0 and info.shadow_refcount <= 0:
            del self.tick_map[tick]

    # -- genesis ------------------------------------------------------------

    def initialize_pool(self, sqrt_price_x96: int, tick: int) -> None:
        """Seed pool state from the on-chain `Initialize` event (or from a
        restored snapshot). Only meaningful before any Mint/Burn/Swap has
        been applied."""
        self.pool.sqrt_price_x96 = sqrt_price_x96
        self.pool.tick = tick
        self.pool.initialized = True

    # -- Mint / Burn ----------------------------------------------------

    def apply_mint(self, tick_lower: int, tick_upper: int, amount: int) -> None:
        for tick, sign in ((tick_lower, 1), (tick_upper, -1)):
            info = self._ensure_tick(tick)
            info.liquidity_gross += amount
            info.liquidity_net += sign * amount
        if tick_lower <= self.pool.tick < tick_upper:
            self.pool.liquidity += amount

    def apply_burn(self, tick_lower: int, tick_upper: int, amount: int) -> None:
        for tick, sign in ((tick_lower, 1), (tick_upper, -1)):
            info = self.tick_map.get(tick)
            if info is None:
                continue  # defensive: malformed/incomplete bootstrap data
            info.liquidity_gross -= amount
            info.liquidity_net -= sign * amount
            self._maybe_delete_tick(tick)
        if tick_lower <= self.pool.tick < tick_upper:
            self.pool.liquidity -= amount

    # -- shadow ticks (agent's own range, not a real historical position) --

    def open_shadow_position(self, tick_lower: int, tick_upper: int) -> None:
        for tick in (tick_lower, tick_upper):
            info = self._ensure_tick(tick)
            info.shadow_refcount += 1

    def close_shadow_position(self, tick_lower: int, tick_upper: int) -> None:
        for tick in (tick_lower, tick_upper):
            info = self.tick_map.get(tick)
            if info is None:
                continue
            info.shadow_refcount = max(0, info.shadow_refcount - 1)
            self._maybe_delete_tick(tick)

    # -- Swap -------------------------------------------------------------

    def apply_swap(self, amount0: int, amount1: int, sqrt_price_x96_new: int, tick_new: int, liquidity_new: int) -> None:
        if not self.pool.initialized:
            # No Initialize event seen (bootstrap started mid-history) --
            # accept the first swap's post-state as our starting point.
            self.pool.sqrt_price_x96 = sqrt_price_x96_new
            self.pool.tick = tick_new
            self.pool.liquidity = liquidity_new
            self.pool.initialized = True
            return

        old_sqrt_p = self.pool.sqrt_price_x96
        old_tick = self.pool.tick
        zero_for_one = amount0 > 0

        if zero_for_one:
            crossed = sorted((t for t in self.tick_map if tick_new < t <= old_tick), reverse=True)
        else:
            crossed = sorted((t for t in self.tick_map if old_tick < t <= tick_new))

        boundaries = [old_sqrt_p] + [sqrt_price_x96_from_tick(t) for t in crossed] + [sqrt_price_x96_new]
        liquidity = self._walk_segments(boundaries, crossed, self.pool.liquidity, zero_for_one)

        if liquidity != liquidity_new:
            self.liquidity_mismatches.append((tick_new, liquidity_new, liquidity))

        self.pool.sqrt_price_x96 = sqrt_price_x96_new
        self.pool.tick = tick_new
        self.pool.liquidity = liquidity_new  # always trust the on-chain reported value

    def _walk_segments(self, boundaries_x96, crossed_ticks, liquidity, zero_for_one) -> int:
        Q96 = 2**96
        for i in range(len(boundaries_x96) - 1):
            sqrt_start = boundaries_x96[i] / Q96
            sqrt_end = boundaries_x96[i + 1] / Q96
            amount0, amount1 = segment_token_deltas(liquidity, sqrt_start, sqrt_end)
            amount_in = amount0 if zero_for_one else amount1
            if amount_in < 0:
                amount_in = 0.0  # numerical noise guard at a zero-length segment
            fee = amount_in * self.fee_pips / (1_000_000 - self.fee_pips)

            if liquidity > 0 and fee > 0:
                fee_growth_delta = int((fee * Q128) // liquidity)
                if zero_for_one:
                    self.pool.fee_growth_global0_x128 = (self.pool.fee_growth_global0_x128 + fee_growth_delta) % Q256
                else:
                    self.pool.fee_growth_global1_x128 = (self.pool.fee_growth_global1_x128 + fee_growth_delta) % Q256

            if i < len(crossed_ticks):
                tick = crossed_ticks[i]
                info = self.tick_map[tick]
                info.fee_growth_outside0_x128 = (self.pool.fee_growth_global0_x128 - info.fee_growth_outside0_x128) % Q256
                info.fee_growth_outside1_x128 = (self.pool.fee_growth_global1_x128 - info.fee_growth_outside1_x128) % Q256
                net = -info.liquidity_net if zero_for_one else info.liquidity_net
                liquidity += net
        return liquidity

    # -- feeGrowthInside ----------------------------------------------------

    def _outside(self, tick: int) -> tuple[int, int]:
        info = self.tick_map.get(tick)
        if info is None:
            return 0, 0
        return info.fee_growth_outside0_x128, info.fee_growth_outside1_x128

    def _below(self, tick: int) -> tuple[int, int]:
        out0, out1 = self._outside(tick)
        if self.pool.tick >= tick:
            return out0, out1
        return (
            (self.pool.fee_growth_global0_x128 - out0) % Q256,
            (self.pool.fee_growth_global1_x128 - out1) % Q256,
        )

    def _above(self, tick: int) -> tuple[int, int]:
        out0, out1 = self._outside(tick)
        if self.pool.tick < tick:
            return out0, out1
        return (
            (self.pool.fee_growth_global0_x128 - out0) % Q256,
            (self.pool.fee_growth_global1_x128 - out1) % Q256,
        )

    def fee_growth_inside(self, tick_lower: int, tick_upper: int) -> tuple[int, int]:
        below0, below1 = self._below(tick_lower)
        above0, above1 = self._above(tick_upper)
        inside0 = (self.pool.fee_growth_global0_x128 - below0 - above0) % Q256
        inside1 = (self.pool.fee_growth_global1_x128 - below1 - above1) % Q256
        return inside0, inside1
