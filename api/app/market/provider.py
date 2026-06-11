"""Market-data providers behind one interface.

`FixtureProvider` synthesizes deterministic, range-independent monthly series
(seeded per ticker+month) — hermetic and free, used by tests and no-network
demos. `LiveProvider` fetches real data (yfinance for indices, FRED for the
risk-free rate); its heavy deps are imported lazily so they're only needed when
MARKET_DATA=live. Both return `{first_of_month: value}` dicts.
"""

from __future__ import annotations

import hashlib
import random
from datetime import date
from typing import Protocol

from app.config import settings

RISK_FREE_TICKER = "DGS3MO"  # FRED 3-month T-bill


def month_range(start: date, end: date) -> list[date]:
    """First-of-month dates from start..end inclusive."""
    out: list[date] = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(date(y, m, 1))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


class MarketDataProvider(Protocol):
    def index_monthly_returns(self, ticker: str, start: date, end: date) -> dict[date, float]: ...

    def risk_free_monthly(self, start: date, end: date) -> dict[date, float]: ...


def _seed(ticker: str, period: date) -> int:
    h = hashlib.md5(ticker.encode()).digest()[:4]
    return int.from_bytes(h, "big") ^ (period.year * 12 + period.month)


class FixtureProvider:
    """Deterministic synthetic data. Values depend only on (ticker, month), so
    they're reproducible and independent of the requested range."""

    def index_monthly_returns(self, ticker: str, start: date, end: date) -> dict[date, float]:
        out = {}
        for m in month_range(start, end):
            rng = random.Random(_seed(ticker, m))
            out[m] = round(rng.gauss(0.006, 0.04), 6)  # ~0.6%/mo, 4% sd
        return out

    def risk_free_monthly(self, start: date, end: date) -> dict[date, float]:
        out = {}
        for m in month_range(start, end):
            rng = random.Random(_seed(RISK_FREE_TICKER, m))
            out[m] = round(max(0.0, 0.03 + rng.gauss(0, 0.005)), 6)  # ~3% annual
        return out


_FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"


class LiveProvider:
    """Real data. yfinance for indices; FRED's public CSV for the risk-free rate
    (fetched via requests so it uses certifi's CA bundle — macOS stdlib SSL can't
    verify FRED otherwise). Heavy deps are imported lazily (live mode only)."""

    def index_monthly_returns(self, ticker: str, start: date, end: date) -> dict[date, float]:
        import yfinance as yf

        df = yf.download(
            ticker, start=start, end=end, interval="1mo",
            auto_adjust=True, progress=False,
        )
        if df.empty:
            return {}
        closes = df["Close"]
        # yfinance returns MultiIndex columns even for a single ticker -> df.
        if hasattr(closes, "columns"):
            closes = closes.iloc[:, 0]
        rets = closes.dropna().pct_change().dropna()
        return {date(d.year, d.month, 1): float(v) for d, v in rets.items()}

    def risk_free_monthly(self, start: date, end: date) -> dict[date, float]:
        import io

        import pandas as pd
        import requests

        params = {"id": RISK_FREE_TICKER, "cosd": f"{start:%Y-%m-%d}", "coed": f"{end:%Y-%m-%d}"}
        resp = requests.get(_FRED_CSV, params=params, timeout=30)
        resp.raise_for_status()

        df = pd.read_csv(io.StringIO(resp.text))
        df.columns = ["date", "rate"]  # observation_date, DGS3MO
        df["date"] = pd.to_datetime(df["date"])
        df["rate"] = pd.to_numeric(df["rate"], errors="coerce")  # "." -> NaN
        df = df.dropna().set_index("date")
        monthly = df["rate"].resample("MS").mean() / 100.0  # annualized % -> decimal
        return {date(d.year, d.month, 1): float(v) for d, v in monthly.items()}


def get_provider() -> MarketDataProvider:
    return LiveProvider() if settings.market_data_mode == "live" else FixtureProvider()
