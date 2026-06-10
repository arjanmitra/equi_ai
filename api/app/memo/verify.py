"""Grounding verifier.

A claim is verified when (a) every ref resolves to a catalog fact, and (b) every
data-like number in its prose matches a value of a *cited* fact, allowing that
fact's legitimate renderings (0.02 -> '2%', 1.2e9 -> '$1.2B', a date -> its year,
a drawdown -> its magnitude). Unverified claims are flagged with their issues,
not dropped.
"""

from __future__ import annotations

import re

from app.memo.numbers import NumberToken, extract_numbers
from app.schemas.catalog import Catalog, Fact
from app.schemas.memo import (
    Claim,
    MemoDraft,
    VerifiedClaim,
    VerifiedMemo,
    VerifiedSection,
)

_DATE_RE = re.compile(r"^(\d{4})-\d{2}-\d{2}")


def _renderings_for_value(v) -> set[float]:
    """Numeric forms a value could legitimately appear as in prose."""
    out: set[float] = set()
    if isinstance(v, bool):
        return out
    if isinstance(v, (int, float)):
        for base in {float(v), abs(float(v))}:
            out.update({base, base * 100, base / 1e3, base / 1e6, base / 1e9})
        return out
    if isinstance(v, str):
        m = _DATE_RE.match(v)
        if m:
            out.add(float(m.group(1)))  # the year
    return out


def _fact_renderings(fact: Fact) -> set[float]:
    if fact.kind == "check":
        out: set[float] = set()
        for key in ("actual", "threshold"):
            val = fact.extra.get(key)
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                out |= _renderings_for_value(val)
        return out
    return _renderings_for_value(fact.value)


def _close(a: float, b: float, decimals: int) -> bool:
    if round(a, decimals) == round(b, decimals):
        return True
    tol = max(0.005, abs(b) * 0.005)
    return abs(a - b) <= tol


def _matches(token: NumberToken, renderings: set[float]) -> bool:
    return any(
        _close(c, r, token.decimals)
        for c in token.candidates
        for r in renderings
    )


def verify_claim(claim: Claim, catalog: Catalog) -> VerifiedClaim:
    issues: list[str] = []

    cited: list[Fact] = []
    for ref in claim.refs:
        fact = catalog.resolve(ref)
        if fact is None:
            issues.append(f"unknown reference: {ref}")
        else:
            cited.append(fact)

    renderings: set[float] = set()
    for fact in cited:
        renderings |= _fact_renderings(fact)

    for token in extract_numbers(claim.text):
        if not token.verifiable:
            continue
        if not _matches(token, renderings):
            issues.append(f"ungrounded number: {token.raw}")

    return VerifiedClaim(
        text=claim.text, refs=claim.refs, verified=not issues, issues=issues
    )


def verify_memo(draft: MemoDraft, catalog: Catalog) -> VerifiedMemo:
    return VerifiedMemo(
        sections=[
            VerifiedSection(
                kind=s.kind,
                title=s.title,
                claims=[verify_claim(c, catalog) for c in s.claims],
            )
            for s in draft.sections
        ]
    )
