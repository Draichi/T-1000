from t1000.fee_engine import FeeEngine, Q128, Q256
from t1000.tick_math import segment_token_deltas, sqrt_price_x96_from_tick

Q96 = 2**96


def test_position_spanning_current_tick_earns_all_global_fee_growth():
    """A position whose range fully contains the active tick, with no
    crossings during the swap, must have feeGrowthInside == feeGrowthGlobal
    exactly -- a basic Uniswap invariant and the simplest possible check."""
    engine = FeeEngine(fee_pips=3000)
    engine.initialize_pool(sqrt_price_x96_from_tick(0), 0)
    engine.apply_mint(tick_lower=-100, tick_upper=100, amount=1000)
    assert engine.pool.liquidity == 1000

    engine.apply_swap(
        amount0=1000,  # zero_for_one: trader pays token0
        amount1=-900,
        sqrt_price_x96_new=sqrt_price_x96_from_tick(-50),
        tick_new=-50,
        liquidity_new=1000,
    )

    assert engine.pool.fee_growth_global0_x128 > 0
    assert engine.pool.fee_growth_global1_x128 == 0  # fee charged in token0 only

    inside0, inside1 = engine.fee_growth_inside(-100, 100)
    assert inside0 == engine.pool.fee_growth_global0_x128
    assert inside1 == engine.pool.fee_growth_global1_x128
    assert not engine.liquidity_mismatches


def test_shadow_position_only_earns_fees_while_price_is_inside_its_range():
    """Hand-computed scenario: real liquidity spans [-100, 100]; a shadow
    (agent) position spans the narrower [-20, 20]. A swap moves price from
    tick 0 up through tick 20 to tick 50 -- crossing the shadow's upper
    boundary partway through. The shadow position should accrue fees only
    for the segment [0, 20] where price was actually inside its range, not
    for [20, 50] where price had already exited above it."""
    fee_pips = 500
    engine = FeeEngine(fee_pips=fee_pips)
    engine.initialize_pool(sqrt_price_x96_from_tick(0), 0)
    engine.apply_mint(tick_lower=-100, tick_upper=100, amount=1000)
    engine.open_shadow_position(-20, 20)

    sqrt_0 = sqrt_price_x96_from_tick(0) / Q96
    sqrt_20 = sqrt_price_x96_from_tick(20) / Q96
    sqrt_50 = sqrt_price_x96_from_tick(50) / Q96

    _, amt1_seg1 = segment_token_deltas(1000, sqrt_0, sqrt_20)
    _, amt1_seg2 = segment_token_deltas(1000, sqrt_20, sqrt_50)
    fee1 = amt1_seg1 * fee_pips / (1_000_000 - fee_pips)
    fee2 = amt1_seg2 * fee_pips / (1_000_000 - fee_pips)
    expected_growth1_seg1 = int((fee1 * Q128) // 1000)
    expected_growth1_seg2 = int((fee2 * Q128) // 1000)

    engine.apply_swap(
        amount0=-1,  # one_for_zero: trader pays token1 (amount0 negative => not > 0)
        amount1=int(amt1_seg1 + amt1_seg2),
        sqrt_price_x96_new=sqrt_price_x96_from_tick(50),
        tick_new=50,
        liquidity_new=1000,  # tick 20 is shadow-only (liquidity_net=0): no change expected
    )

    assert not engine.liquidity_mismatches

    inside0, inside1 = engine.fee_growth_inside(-20, 20)
    assert inside0 == 0
    assert inside1 == expected_growth1_seg1
    assert inside1 != expected_growth1_seg1 + expected_growth1_seg2


def test_never_initialized_tick_defaults_to_zero_outside():
    engine = FeeEngine()
    engine.initialize_pool(sqrt_price_x96_from_tick(0), 0)
    # tick 12345 was never touched by any mint/burn/shadow -- feeGrowthInside
    # for a range using it should not error and should be internally consistent.
    inside0, inside1 = engine.fee_growth_inside(-12345, 12345)
    assert inside0 == 0
    assert inside1 == 0


def test_mod_2_256_wraparound_never_produces_negative():
    engine = FeeEngine()
    engine.initialize_pool(sqrt_price_x96_from_tick(0), 0)
    engine.pool.fee_growth_global0_x128 = 5
    engine.apply_mint(-10, 10, 100)
    tick = engine.tick_map[-10]
    tick.fee_growth_outside0_x128 = 10  # artificially larger than global, forces wraparound
    below0, _ = engine._below(-10)
    assert 0 <= below0 < Q256
