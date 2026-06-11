"""LiveProvider parsing logic — mocked network, so still hermetic.

These lock in the response-shape handling we verified against the real APIs:
yfinance's MultiIndex single-ticker frame, and FRED's daily CSV. Skipped if the
live-mode deps aren't installed.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.market.provider import LiveProvider


def test_index_returns_squeeze_multiindex(monkeypatch):
    yf = pytest.importorskip("yfinance")
    import pandas as pd

    idx = pd.to_datetime(["2023-01-01", "2023-02-01", "2023-03-01"])
    # yfinance returns MultiIndex columns even for a single ticker.
    df = pd.DataFrame(
        {("Close", "SPY"): [100.0, 102.0, 99.0], ("Open", "SPY"): [1, 2, 3]},
        index=idx,
    )
    df.columns = pd.MultiIndex.from_tuples([("Close", "SPY"), ("Open", "SPY")])
    monkeypatch.setattr(yf, "download", lambda *a, **k: df)

    out = LiveProvider().index_monthly_returns("SPY", date(2023, 1, 1), date(2023, 3, 1))
    assert out[date(2023, 2, 1)] == pytest.approx(0.02)  # 102/100 - 1
    assert out[date(2023, 3, 1)] == pytest.approx(99 / 102 - 1)
    assert date(2023, 1, 1) not in out  # first month has no prior -> dropped


def test_risk_free_parses_fred_csv(monkeypatch):
    requests = pytest.importorskip("requests")

    csv = (
        "observation_date,DGS3MO\n"
        "2023-01-03,4.53\n2023-01-10,4.61\n"   # Jan mean 4.57
        "2023-02-01,4.70\n2023-02-15,4.80\n"   # Feb mean 4.75
        "2023-03-01,.\n"                          # missing -> dropped
    )

    class _Resp:
        text = csv

        def raise_for_status(self):
            pass

    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp())

    out = LiveProvider().risk_free_monthly(date(2023, 1, 1), date(2023, 3, 1))
    assert out[date(2023, 1, 1)] == pytest.approx(0.0457)  # 4.57% -> decimal
    assert out[date(2023, 2, 1)] == pytest.approx(0.0475)
    assert date(2023, 3, 1) not in out  # only a missing value that month
