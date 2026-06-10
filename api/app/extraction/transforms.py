"""Deterministic cell transforms applied by the tabular mapper.

These run in code, not in the LLM. The model only *names* which transform to use
(via the mapping plan); the actual value conversion happens here so numbers stay
exact. Each transform returns a Python value or raises ValueError on bad input.
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime
from typing import Any

from dateutil import parser as date_parser

from app.schemas.mapping import Transform

_CURRENCY_RE = re.compile(r"[^0-9.\-]")
_NUMERIC_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip().lower() in {
        "",
        "na",
        "n/a",
        "nan",
        "none",
        "null",
        "-",
    }:
        return True
    return False


def _to_number(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    match = _NUMERIC_RE.search(str(value).replace(",", ""))
    if not match:
        raise ValueError(f"no numeric content in {value!r}")
    return float(match.group())


def percent_to_decimal(value: Any) -> float:
    """'2%' -> 0.02, '2 and 20' handled upstream. A bare 2.0 is treated as 2%."""
    num = _to_number(value)
    return num / 100.0


# Magnitude suffixes common in fund data ("$450M", "$2.1B", "$85MM").
_MAGNITUDE = [("bn", 1e9), ("b", 1e9), ("mm", 1e6), ("m", 1e6), ("k", 1e3), ("t", 1e12)]


def strip_currency(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower()
    multiplier = 1.0
    for suffix, mult in _MAGNITUDE:
        if text.endswith(suffix):
            multiplier = mult
            break
    cleaned = _CURRENCY_RE.sub("", text)
    if cleaned in {"", "-", "."}:
        raise ValueError(f"no numeric content in {value!r}")
    return float(cleaned) * multiplier


def parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    # Anchor partial dates (e.g. "Jan 2018", "03/2020") to the 1st rather than
    # letting dateutil fill in today's day.
    default = datetime(2000, 1, 1)
    return date_parser.parse(str(value), dayfirst=False, default=default).date()


def parse_int(value: Any) -> int:
    return int(round(_to_number(value)))


def parse_float(value: Any) -> float:
    return _to_number(value)


_TRANSFORMS = {
    Transform.NONE: lambda v: v.strip() if isinstance(v, str) else v,
    Transform.PERCENT_TO_DECIMAL: percent_to_decimal,
    Transform.STRIP_CURRENCY: strip_currency,
    Transform.PARSE_DATE: parse_date,
    Transform.PARSE_INT: parse_int,
    Transform.PARSE_FLOAT: parse_float,
}


def apply_transform(value: Any, transform: Transform) -> Any:
    """Apply a transform, short-circuiting missing values to None."""
    if _is_missing(value):
        return None
    fn = _TRANSFORMS.get(transform, _TRANSFORMS[Transform.NONE])
    return fn(value)
