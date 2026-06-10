"""Metric result schemas.

`PartialMetrics` holds the metrics computable from a fund's own return series
alone (no benchmark/risk-free needed). Sharpe and correlation join in a later
step once the benchmark + risk-free providers land.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class PartialMetrics(BaseModel):
    n_obs: int
    annualized_volatility: float | None = None  # stdev(monthly, ddof=1) * sqrt(12)
    max_drawdown: float | None = None  # worst peak-to-trough, <= 0
    annualized_return: float | None = None  # geometric CAGR
    cumulative_return: float | None = None  # total compounded return
    low_confidence: bool = False  # fewer than MIN_OBS observations


class FundMetricsOut(BaseModel):
    """API view of a fund's computed metrics."""

    fund_id: str
    fund_name: str
    business_key: str
    benchmark_ticker: str | None
    n_obs: int
    annualized_volatility: float | None
    max_drawdown: float | None
    annualized_return: float | None
    cumulative_return: float | None
    sharpe: float | None
    correlation_benchmark: float | None
    period_start: date | None
    period_end: date | None
    low_confidence: bool
    inputs: dict
