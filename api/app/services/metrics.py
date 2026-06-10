"""Compute per-fund metrics for an upload and persist them as FundMetrics.

For each fund: pull its return series, map strategy -> benchmark (with optional
override), fetch the cached benchmark + risk-free over the fund's date range,
compute the full metric set, and upsert one FundMetrics row carrying an
inputs_json audit record. Metrics are upload-scoped; runs read them.
"""

from __future__ import annotations

import statistics

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.db.models import _now
from app.market import get_index_series, get_risk_free_series, get_provider
from app.market.benchmarks import benchmark_for
from app.market.provider import MarketDataProvider, RISK_FREE_TICKER
from app.metrics import (
    align_series,
    correlation,
    sharpe_ratio,
    summarize_returns,
)
from app.schemas.metrics import FundMetricsOut


def compute_metrics_for_upload(
    db: Session,
    upload_id: str,
    overrides: dict[str, str] | None = None,
    provider: MarketDataProvider | None = None,
) -> list[models.FundMetrics]:
    provider = provider or get_provider()
    funds = db.scalars(
        select(models.Fund).where(models.Fund.upload_id == upload_id)
    ).all()
    out = [_compute_one(db, fund, overrides or {}, provider) for fund in funds]
    db.commit()
    return out


def _compute_one(
    db: Session, fund: models.Fund, overrides: dict[str, str], provider: MarketDataProvider
) -> models.FundMetrics:
    series = {o.period: o.value for o in fund.returns}
    ordered = [series[p] for p in sorted(series)]
    partial = summarize_returns(ordered)
    ticker, note = benchmark_for(fund.strategy, overrides)

    period_start = min(series) if series else None
    period_end = max(series) if series else None
    sharpe = corr = rf_annual = None
    bench_months = aligned = 0

    if series:
        rf = get_risk_free_series(db, period_start, period_end, provider)
        rf_annual = sum(rf.values()) / len(rf) if rf else 0.0
        bench = get_index_series(db, ticker, period_start, period_end, provider)
        bench_months = len(bench)

        if partial.annualized_volatility:  # not None and not 0
            try:
                sharpe = sharpe_ratio(ordered, rf_annual)
            except ValueError:
                sharpe = None

        fa, fb = align_series(series, bench)
        aligned = len(fa)
        if aligned >= 2:
            try:
                corr = correlation(fa, fb)
            except (ValueError, statistics.StatisticsError):
                corr = None

    inputs = {
        "n_obs": partial.n_obs,
        "period_start": period_start.isoformat() if period_start else None,
        "period_end": period_end.isoformat() if period_end else None,
        "benchmark_ticker": ticker,
        "benchmark_note": note,
        "risk_free_ticker": RISK_FREE_TICKER,
        "rf_annual": rf_annual,
        "benchmark_months": bench_months,
        "aligned_months": aligned,
    }

    fm = fund.metrics or models.FundMetrics(fund_id=fund.id)
    fm.computed_at = _now()
    fm.benchmark_ticker = ticker
    fm.n_obs = partial.n_obs
    fm.annualized_volatility = partial.annualized_volatility
    fm.max_drawdown = partial.max_drawdown
    fm.annualized_return = partial.annualized_return
    fm.cumulative_return = partial.cumulative_return
    fm.sharpe = sharpe
    fm.correlation_benchmark = corr
    fm.period_start = period_start
    fm.period_end = period_end
    fm.low_confidence = partial.low_confidence
    fm.inputs_json = inputs
    if fund.metrics is None:
        db.add(fm)
    return fm


def serialize_metrics(fm: models.FundMetrics) -> FundMetricsOut:
    return FundMetricsOut(
        fund_id=fm.fund_id,
        fund_name=fm.fund.name,
        business_key=fm.fund.business_key,
        benchmark_ticker=fm.benchmark_ticker,
        n_obs=fm.n_obs,
        annualized_volatility=fm.annualized_volatility,
        max_drawdown=fm.max_drawdown,
        annualized_return=fm.annualized_return,
        cumulative_return=fm.cumulative_return,
        sharpe=fm.sharpe,
        correlation_benchmark=fm.correlation_benchmark,
        period_start=fm.period_start,
        period_end=fm.period_end,
        low_confidence=fm.low_confidence,
        inputs=fm.inputs_json or {},
    )
