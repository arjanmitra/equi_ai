"""Unit tests for the deterministic transforms — the numbers must stay exact."""

from __future__ import annotations

import datetime as dt

import pytest

from app.extraction.transforms import apply_transform
from app.schemas.mapping import Transform


@pytest.mark.parametrize(
    "raw,expected",
    [("2%", 0.02), ("20%", 0.20), (1.5, 0.015), ("17.5%", 0.175)],
)
def test_percent_to_decimal(raw, expected):
    assert apply_transform(raw, Transform.PERCENT_TO_DECIMAL) == pytest.approx(expected)


@pytest.mark.parametrize(
    "raw,expected",
    [("150 bps", 0.015), ("200bps", 0.02), ("175 bp", 0.0175)],
)
def test_bps_to_decimal(raw, expected):
    assert apply_transform(raw, Transform.BPS_TO_DECIMAL) == pytest.approx(expected)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("$1,200,000,000", 1_200_000_000.0),
        ("$85,000,000", 85_000_000.0),
        ("$450M", 450_000_000.0),
        ("$2.1B", 2_100_000_000.0),
        ("$85MM", 85_000_000.0),
        (450.0, 450.0),
    ],
)
def test_strip_currency(raw, expected):
    assert apply_transform(raw, Transform.STRIP_CURRENCY) == pytest.approx(expected)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Jan 2018", dt.date(2018, 1, 1)),
        ("2015-06-01", dt.date(2015, 6, 1)),
        ("03/2020", dt.date(2020, 3, 1)),
    ],
)
def test_parse_date(raw, expected):
    assert apply_transform(raw, Transform.PARSE_DATE) == expected


def test_missing_values_short_circuit_to_none():
    for missing in ["", "  ", "N/A", "na", "-", None]:
        assert apply_transform(missing, Transform.STRIP_CURRENCY) is None


def test_parse_int_from_messy_string():
    assert apply_transform("30 days", Transform.PARSE_INT) == 30
