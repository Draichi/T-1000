import pytest

from t1000.gas_model import (
    DEFAULT_GAS_UNITS,
    action_gas_cost_usd,
    calibrate_gas_units_from_median,
    gas_cost_usd,
)


def test_gas_cost_usd_basic_arithmetic():
    # 100,000 gas units * 50 gwei base fee = 0.005 ETH; at $3000/ETH -> $15
    cost = gas_cost_usd(gas_units=100_000, base_fee_per_gas_wei=50e9, usd_per_eth=3000.0)
    assert cost == pytest.approx(15.0)


def test_action_gas_cost_usd_sums_components():
    cost_burn_only = action_gas_cost_usd(["burn"], base_fee_per_gas_wei=50e9, usd_per_eth=3000.0)
    cost_burn_collect = action_gas_cost_usd(["burn", "collect"], base_fee_per_gas_wei=50e9, usd_per_eth=3000.0)
    assert cost_burn_collect > cost_burn_only
    expected = gas_cost_usd(
        DEFAULT_GAS_UNITS["burn"] + DEFAULT_GAS_UNITS["collect"], 50e9, 3000.0
    )
    assert cost_burn_collect == pytest.approx(expected)


def test_calibrate_gas_units_uses_median_and_falls_back_to_defaults():
    samples = {"mint": [400_000, 420_000, 440_000], "burn": []}
    calibrated = calibrate_gas_units_from_median(samples)
    assert calibrated["mint"] == 420_000
    assert calibrated["burn"] == DEFAULT_GAS_UNITS["burn"]  # no samples -> fallback
    assert calibrated["collect"] == DEFAULT_GAS_UNITS["collect"]  # untouched key
