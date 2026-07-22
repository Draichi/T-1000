"""Gas cost estimation for LP actions: calibrated (or prior) gas-unit
estimates per underlying contract call, combined with the historical
base_fee_per_gas and USD/ETH price at the time of the transaction.

Order-of-magnitude priors below are placeholders until
`calibrate_gas_units_from_median` is run against real NonfungiblePositionManager
transactions for this pool in `build_dataset.py`.
"""
import statistics

DEFAULT_GAS_UNITS = {
    "mint": 450_000,       # increaseLiquidity / mint a new position
    "burn": 150_000,       # decreaseLiquidity
    "collect": 130_000,
}


def gas_cost_usd(gas_units: int, base_fee_per_gas_wei: float, usd_per_eth: float) -> float:
    eth_spent = gas_units * base_fee_per_gas_wei / 1e18
    return eth_spent * usd_per_eth


def action_gas_cost_usd(
    components: list[str],
    base_fee_per_gas_wei: float,
    usd_per_eth: float,
    gas_units_table: dict | None = None,
) -> float:
    """components: e.g. ["burn", "collect", "mint"] for a rebalance."""
    table = gas_units_table or DEFAULT_GAS_UNITS
    total_units = sum(table[c] for c in components)
    return gas_cost_usd(total_units, base_fee_per_gas_wei, usd_per_eth)


def calibrate_gas_units_from_median(samples: dict[str, list[int]]) -> dict:
    """samples: {"mint": [receipt_gas_used, ...], "burn": [...], "collect": [...]}
    -> median gas units per action type, falling back to DEFAULT_GAS_UNITS
    for any action type with no observed samples."""
    calibrated = dict(DEFAULT_GAS_UNITS)
    for action, values in samples.items():
        if values:
            calibrated[action] = int(statistics.median(values))
    return calibrated
