"""Extract numeric tokens from prose for grounding verification.

Each token records its written form, value, decimal precision, and unit
(percent / bps / magnitude), from which we derive candidate true magnitudes.
Only "data-like" tokens are verified — unit-bearing, fractional, large, or
negative — so incidental small integers ("the top 3 funds") don't trip the gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# $ prefix, the number (commas/decimals), and an optional immediately-following
# unit. Single-letter magnitude suffixes must not be followed by another letter
# (so "12 months" doesn't read as 12 million).
_NUM_RE = re.compile(
    r"(?P<dollar>\$)?"
    r"(?P<num>-?\d[\d,]*(?:\.\d+)?)"
    r"(?P<unit>%|bps|bp|bn|mm|[bmkt](?![a-z])|\s?(?:billion|million|thousand|bps))?",
    re.IGNORECASE,
)

_MULT = {"b": 1e9, "m": 1e6, "k": 1e3, "t": 1e12}


def _canon_unit(suf: str | None) -> str | None:
    if not suf:
        return None
    s = suf.strip().lower()
    if s == "%":
        return "percent"
    if s in ("bps", "bp"):
        return "bps"
    if s in ("bn", "b", "billion"):
        return "b"
    if s in ("mm", "m", "million"):
        return "m"
    if s in ("k", "thousand"):
        return "k"
    if s == "t":
        return "t"
    return None


@dataclass
class NumberToken:
    raw: str
    value: float
    decimals: int
    unit: str | None  # 'percent' | 'bps' | 'b' | 'm' | 'k' | 't' | None

    @property
    def candidates(self) -> set[float]:
        """Plausible true magnitudes this token could denote."""
        v = self.value
        if self.unit == "percent":
            return {v / 100.0, v}
        if self.unit == "bps":
            return {v / 10000.0, v}
        if self.unit in _MULT:
            return {v * _MULT[self.unit], v}
        return {v, v / 100.0}  # bare number: allow percent-without-%

    @property
    def verifiable(self) -> bool:
        # Gate only on data-like figures, not incidental small counts.
        return (
            self.unit is not None
            or self.decimals > 0
            or abs(self.value) >= 100
            or self.value < 0
        )


def extract_numbers(text: str) -> list[NumberToken]:
    tokens: list[NumberToken] = []
    for m in _NUM_RE.finditer(text):
        num = m.group("num").replace(",", "")
        try:
            value = float(num)
        except ValueError:
            continue
        decimals = len(num.split(".")[1]) if "." in num else 0
        tokens.append(
            NumberToken(
                raw=m.group(0).strip(),
                value=value,
                decimals=decimals,
                unit=_canon_unit(m.group("unit")),
            )
        )
    return tokens
