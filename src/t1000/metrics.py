"""Performance metrics: Sharpe ratio, max drawdown, gas-adjusted APR."""
import numpy as np


def returns_from_values(values: list) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if len(values) < 2:
        return np.array([])
    return values[1:] / values[:-1] - 1.0


def sharpe_ratio(values: list, periods_per_year: float) -> float:
    rets = returns_from_values(values)
    if len(rets) < 2 or rets.std() == 0:
        return 0.0
    return float(rets.mean() / rets.std() * np.sqrt(periods_per_year))


def max_drawdown(values: list) -> float:
    values = np.asarray(values, dtype=np.float64)
    if len(values) == 0:
        return 0.0
    running_max = np.maximum.accumulate(values)
    drawdowns = (values - running_max) / running_max
    return float(drawdowns.min())


def gas_adjusted_apr(initial_value: float, final_value: float, hours: float) -> float:
    if initial_value <= 0 or hours <= 0:
        return 0.0
    total_return = final_value / initial_value - 1.0
    years = hours / (24 * 365)
    return float(total_return / years) if years > 0 else 0.0


def compute_episode_metrics(portfolio_values: list, step_hours: float = 1.0) -> dict:
    hours = step_hours * max(len(portfolio_values) - 1, 0)
    periods_per_year = (24 / step_hours) * 365
    return {
        "episode_pnl_usd": float(portfolio_values[-1] - portfolio_values[0]),
        "sharpe_ratio": sharpe_ratio(portfolio_values, periods_per_year),
        "max_drawdown": max_drawdown(portfolio_values),
        "gas_adjusted_apr": gas_adjusted_apr(portfolio_values[0], portfolio_values[-1], hours),
        "final_value_usd": portfolio_values[-1],
        "n_steps": len(portfolio_values),
    }
