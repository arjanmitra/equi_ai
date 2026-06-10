"""End-to-end extraction tests against the messy fixture.

These run OFFLINE (no API key) via the heuristic mapping plan, proving the
tabular path works end-to-end without a network — which is what CI and a
no-key demo rely on.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from app.extraction import extract
from app.schemas.fund import Fund

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def result():
    raw = (FIXTURES / "messy_universe.csv").read_bytes()
    return extract(raw, "messy_universe.csv", Fund)


def test_all_rows_extracted(result):
    assert result.strategy == "tabular"
    assert result.report.records_ok == 5
    assert result.report.records_failed == 0
    assert len(result.records) == 5


def test_semicolon_delimiter_sniffed(result):
    # The fixture uses ';'. If the delimiter sniff failed we'd get one column
    # and the records would be unmapped/empty.
    names = {r["name"] for r in result.records}
    assert "Alpha Macro Partners" in names


def test_fees_normalized_to_decimals(result):
    alpha = next(r for r in result.records if r["name"] == "Alpha Macro Partners")
    assert alpha["management_fee"] == pytest.approx(0.02)
    assert alpha["performance_fee"] == pytest.approx(0.20)


def test_currency_and_dates_parsed(result):
    alpha = next(r for r in result.records if r["name"] == "Alpha Macro Partners")
    assert alpha["aum_usd"] == pytest.approx(1_200_000_000.0)
    assert alpha["inception_date"] == dt.date(2018, 1, 1).isoformat()


def test_missing_aum_is_none_not_error(result):
    echo = next(r for r in result.records if r["name"] == "Echo Multi-Strat")
    assert echo["aum_usd"] is None


def test_provenance_links_back_to_source_column(result):
    fee_prov = [
        p for p in result.provenance if p.target_field == "management_fee"
    ]
    assert fee_prov, "expected provenance for management_fee"
    assert all(p.source.startswith("column:") for p in fee_prov)
    # The raw value is preserved alongside the normalized one — this is what the
    # audit trail renders.
    alpha_fee = next(
        p for p in fee_prov if result.records[p.record_index]["name"]
        == "Alpha Macro Partners"
    )
    assert alpha_fee.raw_value == "2%"
    assert alpha_fee.normalized_value == pytest.approx(0.02)
