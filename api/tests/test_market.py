"""Market-data provider + caching tests (hermetic — FixtureProvider only)."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models
from app.db.database import Base
from app.market import get_index_series, get_risk_free_series, month_range
from app.market.provider import FixtureProvider

START, END = date(2022, 1, 1), date(2022, 6, 1)


def test_month_range_inclusive():
    months = month_range(date(2022, 11, 1), date(2023, 2, 1))
    assert months == [date(2022, 11, 1), date(2022, 12, 1), date(2023, 1, 1), date(2023, 2, 1)]


def test_fixture_provider_is_deterministic_and_range_independent():
    p = FixtureProvider()
    a = p.index_monthly_returns("SPY", START, END)
    b = p.index_monthly_returns("SPY", START, END)
    assert a == b  # deterministic
    # Same month has the same value even when requested in a wider range.
    wide = p.index_monthly_returns("SPY", date(2021, 1, 1), date(2023, 1, 1))
    assert wide[date(2022, 3, 1)] == a[date(2022, 3, 1)]
    # Different tickers differ.
    assert p.index_monthly_returns("AGG", START, END) != a


class SpyProvider:
    """Wraps FixtureProvider and counts fetches, to prove caching."""

    def __init__(self):
        self.inner = FixtureProvider()
        self.index_calls = 0
        self.rf_calls = 0

    def index_monthly_returns(self, ticker, start, end):
        self.index_calls += 1
        return self.inner.index_monthly_returns(ticker, start, end)

    def risk_free_monthly(self, start, end):
        self.rf_calls += 1
        return self.inner.risk_free_monthly(start, end)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_index_series_cached_after_first_fetch(db):
    spy = SpyProvider()
    first = get_index_series(db, "SPY", START, END, provider=spy)
    second = get_index_series(db, "SPY", START, END, provider=spy)

    assert first == second
    assert len(first) == 6  # Jan..Jun 2022
    assert spy.index_calls == 1  # second call served from cache
    # Rows persisted in BenchmarkSeries.
    rows = list(db.scalars(select(models.BenchmarkSeries).where(models.BenchmarkSeries.ticker == "SPY")))
    assert len(rows) == 6


def test_risk_free_series_cached(db):
    spy = SpyProvider()
    get_risk_free_series(db, START, END, provider=spy)
    get_risk_free_series(db, START, END, provider=spy)
    assert spy.rf_calls == 1
    rows = list(db.scalars(select(models.BenchmarkSeries).where(models.BenchmarkSeries.ticker == "DGS3MO")))
    assert len(rows) == 6
    assert all(r.value >= 0 for r in rows)
