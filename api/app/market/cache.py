"""Caching layer over the market provider.

Reads cached `BenchmarkSeries` rows first; only calls the provider for months
that are missing, then stores them. This means the external API (or fixture) is
hit at most once per (ticker, month), and a mandate run never refetches.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.market.provider import (
    RISK_FREE_TICKER,
    MarketDataProvider,
    get_provider,
    month_range,
)


def _cached(
    db: Session,
    ticker: str,
    start: date,
    end: date,
    fetcher: Callable[[date, date], dict[date, float]],
) -> dict[date, float]:
    rows = db.scalars(
        select(models.BenchmarkSeries).where(
            models.BenchmarkSeries.ticker == ticker,
            models.BenchmarkSeries.period >= start,
            models.BenchmarkSeries.period <= end,
        )
    ).all()
    cached = {r.period: r.value for r in rows}

    months = month_range(start, end)
    if not all(m in cached for m in months):
        fetched = fetcher(start, end)
        for period, value in fetched.items():
            if period not in cached:
                db.add(
                    models.BenchmarkSeries(ticker=ticker, period=period, value=value)
                )
                cached[period] = value
        db.commit()

    return {m: cached[m] for m in months if m in cached}


def get_index_series(
    db: Session,
    ticker: str,
    start: date,
    end: date,
    provider: MarketDataProvider | None = None,
) -> dict[date, float]:
    provider = provider or get_provider()
    return _cached(
        db, ticker, start, end,
        lambda s, e: provider.index_monthly_returns(ticker, s, e),
    )


def get_risk_free_series(
    db: Session,
    start: date,
    end: date,
    provider: MarketDataProvider | None = None,
) -> dict[date, float]:
    provider = provider or get_provider()
    return _cached(
        db, RISK_FREE_TICKER, start, end,
        lambda s, e: provider.risk_free_monthly(s, e),
    )
