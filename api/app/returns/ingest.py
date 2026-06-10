"""Ingest a monthly return series into canonical (fund_ref, period, value) triples.

Two shapes are supported (per the agreed scope):

  long        fund, date, return            -> one row per observation
  wide-by-date  one row per fund, date columns (Jan-18, Feb-18, ...) -> melt

Shape detection is deterministic (date-parsing of headers vs cell values), so no
LLM is needed for time-series structure — which keeps this hermetic and cheap.
Column roles are resolved by header synonyms first, falling back to value typing.
Returns are normalized to decimals and periods to the first of the month.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Callable

from dateutil import parser as dtp

from app.extraction.loaders import route
from app.extraction.loaders.base import TabularContent
from app.schemas.extraction import IssueLevel, ValidationReport
from app.schemas.returns import ReturnRecord, ReturnsExtraction

# Minimum date-named columns to treat a table as wide-by-date.
_WIDE_THRESHOLD = 3

_FUND_SYNS = ["fund", "name", "manager", "account", "id", "code"]
_PERIOD_SYNS = ["date", "period", "month", "as of", "asof", "month end"]
_VALUE_SYNS = ["return", "ret", "performance", "perf", "pnl", "net", "monthly", "value"]

_PURE_NUMBER = re.compile(r"-?\d+(?:\.\d+)?$")
_NUMERIC = re.compile(r"-?\d+(?:\.\d+)?")
_MISSING = {"", "na", "n/a", "nan", "none", "null", "-"}

# Tried before dateutil so month-year headers like "Jan-23" resolve the trailing
# number as a YEAR, not a day. Two-digit-year forms come first so they win.
_MONTH_YEAR_FORMATS = [
    "%b-%y", "%b %y", "%b/%y",
    "%b-%Y", "%b %Y", "%B %Y", "%B %y",
    "%Y-%m", "%Y/%m", "%m/%Y", "%m-%Y",
]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def _try_date(value) -> date | None:
    """Parse a header or cell as a month, or None. Pure numbers are not dates."""
    s = str(value).strip()
    if not s or _PURE_NUMBER.match(s):
        return None
    for fmt in _MONTH_YEAR_FORMATS:
        try:
            d = datetime.strptime(s, fmt)
            return date(d.year, d.month, 1)
        except ValueError:
            continue
    try:
        d = dtp.parse(s, default=datetime(2000, 1, 1))
    except (ValueError, OverflowError):
        return None
    return date(d.year, d.month, 1)  # normalize to first of month


def _try_return(value) -> float | None:
    """Parse a return cell to a decimal. '1.2%' or '1.2' -> 0.012; '0.012' -> 0.012."""
    s = str(value).strip()
    if s.lower() in _MISSING:
        return None
    pct = "%" in s
    m = _NUMERIC.search(s.replace(",", ""))
    if not m:
        return None
    v = float(m.group())
    if pct:
        return v / 100.0
    # No %: a magnitude >= 1 is almost certainly a percent written as a number
    # (a +100% monthly return is implausible); below 1 we treat it as a decimal.
    return v / 100.0 if abs(v) >= 1 else v


def _frac(values: list, pred: Callable) -> float:
    vals = [v for v in values if v not in (None, "")]
    if not vals:
        return 0.0
    return sum(1 for v in vals if pred(v)) / len(vals)


def _pick(cols: list[str], syns: list[str]) -> str | None:
    for c in cols:
        n = _norm(c)
        if any(s in n or n in s for s in syns):
            return c
    return None


def _classify(content: TabularContent) -> tuple[str, dict]:
    cols = content.columns
    rows = content.sample_rows(12)

    def col_values(c):
        return [r[c] for r in rows if r.get(c) not in (None, "")]

    date_named = [c for c in cols if _try_date(c) is not None]
    value_date = {c: _frac(col_values(c), lambda x: _try_date(x) is not None) >= 0.6 for c in cols}
    value_num = {c: _frac(col_values(c), lambda x: _try_return(x) is not None) >= 0.6 for c in cols}

    if len(date_named) >= _WIDE_THRESHOLD:
        non_date = [c for c in cols if c not in date_named]
        id_col = _pick(non_date, _FUND_SYNS) or next(
            (c for c in non_date if not value_num[c]), non_date[0] if non_date else None
        )
        return "wide", {"date_cols": date_named, "id_col": id_col}

    period_col = _pick(cols, _PERIOD_SYNS) or next(
        (c for c in cols if value_date[c]), None
    )
    rest = [c for c in cols if c != period_col]
    value_col = _pick(rest, _VALUE_SYNS) or next(
        (c for c in rest if value_num[c]), None
    )
    fund_col = _pick(
        [c for c in cols if c not in (period_col, value_col)], _FUND_SYNS
    ) or next((c for c in cols if c not in (period_col, value_col)), None)
    return "long", {"period_col": period_col, "value_col": value_col, "fund_col": fund_col}


def _extract_long(content: TabularContent, info: dict, report: ValidationReport) -> list[ReturnRecord]:
    period_col, value_col, fund_col = info["period_col"], info["value_col"], info["fund_col"]
    if not (period_col and value_col and fund_col):
        report.add(
            IssueLevel.ERROR,
            f"could not identify long-format columns "
            f"(fund={fund_col}, period={period_col}, value={value_col})",
        )
        return []

    records: list[ReturnRecord] = []
    for _, row in content.df.iterrows():
        fund_ref = str(row[fund_col]).strip()
        period = _try_date(row[period_col])
        value = _try_return(row[value_col])
        if not fund_ref or period is None or value is None:
            report.records_failed += 1
            continue
        records.append(ReturnRecord(fund_ref=fund_ref, period=period, value=value))
    report.add(
        IssueLevel.INFO,
        f"long format: fund='{fund_col}', period='{period_col}', value='{value_col}'",
    )
    return records


def _extract_wide(content: TabularContent, info: dict, report: ValidationReport) -> list[ReturnRecord]:
    date_cols, id_col = info["date_cols"], info["id_col"]
    if not id_col:
        report.add(IssueLevel.ERROR, "could not identify the fund identity column")
        return []

    records: list[ReturnRecord] = []
    for _, row in content.df.iterrows():
        fund_ref = str(row[id_col]).strip()
        if not fund_ref:
            continue
        for dc in date_cols:
            period = _try_date(dc)
            value = _try_return(row[dc])
            if period is None or value is None:
                continue  # blank cell — skip, not an error
            records.append(ReturnRecord(fund_ref=fund_ref, period=period, value=value))
    report.add(
        IssueLevel.INFO,
        f"wide format: id='{id_col}', {len(date_cols)} date columns melted",
    )
    return records


def ingest_returns(raw: bytes, filename: str) -> ReturnsExtraction:
    report = ValidationReport()
    try:
        _mime, loader = route(raw, filename)
        content = loader.load(raw, filename)
    except Exception as exc:  # noqa: BLE001 - per-file isolation
        report.add(IssueLevel.ERROR, f"failed to load file: {exc}")
        return ReturnsExtraction(source_name=filename, shape="none", records=[], report=report)

    if not isinstance(content, TabularContent):
        report.add(IssueLevel.ERROR, "returns must be a tabular file (CSV/XLSX)")
        return ReturnsExtraction(source_name=filename, shape="none", records=[], report=report)

    shape, info = _classify(content)
    records = _extract_wide(content, info, report) if shape == "wide" else _extract_long(content, info, report)
    report.total_rows = content.row_count
    report.records_ok = len(records)
    return ReturnsExtraction(
        source_name=filename, shape=shape, records=records, report=report
    )
