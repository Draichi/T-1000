import pytest

from t1000.metrics import (
    compute_episode_metrics,
    gas_adjusted_apr,
    max_drawdown,
    returns_from_values,
    sharpe_ratio,
)


def test_returns_from_values_basic():
    rets = returns_from_values([100, 110, 99])
    assert rets == pytest.approx([0.10, -0.10], abs=1e-9)


def test_returns_from_values_too_short():
    assert len(returns_from_values([100])) == 0
    assert len(returns_from_values([])) == 0


def test_sharpe_ratio_zero_for_constant_values():
    assert sharpe_ratio([100, 100, 100, 100], periods_per_year=365) == 0.0


def test_sharpe_ratio_positive_for_upward_trend():
    values = [100, 101, 102, 103, 104, 105]
    assert sharpe_ratio(values, periods_per_year=365) > 0


def test_max_drawdown_no_drop_is_zero():
    assert max_drawdown([100, 110, 120]) == pytest.approx(0.0)


def test_max_drawdown_detects_worst_drop():
    # peak 120 -> trough 90 => -25%
    dd = max_drawdown([100, 120, 90, 110])
    assert dd == pytest.approx(-0.25)


def test_gas_adjusted_apr_doubling_in_one_year():
    apr = gas_adjusted_apr(initial_value=100, final_value=200, hours=24 * 365)
    assert apr == pytest.approx(1.0, abs=1e-6)


def test_gas_adjusted_apr_zero_hours_or_initial_is_safe():
    assert gas_adjusted_apr(0, 100, 100) == 0.0
    assert gas_adjusted_apr(100, 100, 0) == 0.0


def test_compute_episode_metrics_shape():
    values = [10_000, 10_050, 10_020, 10_100]
    metrics = compute_episode_metrics(values, step_hours=1.0)
    assert metrics["n_steps"] == 4
    assert metrics["final_value_usd"] == 10_100
    assert metrics["episode_pnl_usd"] == pytest.approx(100)
    assert "sharpe_ratio" in metrics
    assert "max_drawdown" in metrics
    assert "gas_adjusted_apr" in metrics
