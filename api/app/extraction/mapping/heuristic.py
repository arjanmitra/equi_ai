"""Offline heuristic mapping plan.

Used when no LLM key is present (tests/CI, offline demo) so the tabular path
runs end-to-end without a network. It is intentionally simple: a synonym table
for the canonical fund fields plus fuzzy token matching, with a transform guess
based on the target field's name. The LLM mapper supersedes this when available.
"""

from __future__ import annotations

import difflib
import re

from pydantic import BaseModel

from app.extraction.field_spec import field_specs
from app.schemas.mapping import ColumnMap, MappingPlan, Transform

# Known aliases for the canonical Fund fields. Lowercased, punctuation-stripped.
_SYNONYMS: dict[str, list[str]] = {
    "fund_id": ["fund id", "id", "ticker", "code", "fund code", "identifier"],
    "name": ["fund name", "manager", "manager name", "fund", "strategy name"],
    "strategy": ["strategy", "style", "approach", "asset class", "sub strategy"],
    "redemption_frequency": ["redemption", "liquidity", "redemption frequency", "dealing"],
    "notice_period_days": ["notice", "notice period", "notice days", "redemption notice"],
    "lockup_months": ["lockup", "lock up", "lock-up", "lockup period", "lock up months"],
    "management_fee": ["management fee", "mgmt fee", "mgmt", "annual fee", "base fee"],
    "performance_fee": ["performance fee", "perf fee", "incentive fee", "carry"],
    "aum_usd": ["aum", "assets", "assets under management", "fund size", "size"],
    "inception_date": ["inception", "inception date", "launch", "launch date", "vintage"],
    "notes": ["notes", "comments", "qualitative", "remarks", "commentary"],
}

# Transform guess keyed by target field name fragments.
_FEE_FIELDS = {"management_fee", "performance_fee"}
_DATE_FIELDS = {"inception_date"}
_INT_FIELDS = {"notice_period_days", "lockup_months"}
_CURRENCY_FIELDS = {"aum_usd"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", s.lower()).strip()


def _guess_transform(target_field: str) -> Transform:
    if target_field in _FEE_FIELDS:
        return Transform.PERCENT_TO_DECIMAL
    if target_field in _DATE_FIELDS:
        return Transform.PARSE_DATE
    if target_field in _INT_FIELDS:
        return Transform.PARSE_INT
    if target_field in _CURRENCY_FIELDS:
        return Transform.STRIP_CURRENCY
    return Transform.NONE


def _score(ncol: str, candidates: list[str]) -> float:
    score = max(
        (difflib.SequenceMatcher(None, ncol, cand).ratio() for cand in candidates),
        default=0.0,
    )
    # Substring containment is a strong signal fuzzy ratio underweights.
    if any(cand and (cand in ncol or ncol in cand) for cand in candidates):
        score = max(score, 0.9)
    return score


def heuristic_plan(columns: list[str], target: type[BaseModel]) -> MappingPlan:
    norm_cols = {col: _norm(col) for col in columns}

    # Score every (field, column) pair, then assign greedily by descending
    # score. This stops a weak match on one field from stealing a column that
    # another field matches strongly (e.g. fund_id vs name on "Fund Name").
    scored: list[tuple[float, str, str]] = []
    for spec in field_specs(target):
        candidates = _SYNONYMS.get(spec.name, []) + [_norm(spec.name)]
        for col, ncol in norm_cols.items():
            s = _score(ncol, candidates)
            if s >= 0.6:
                scored.append((s, spec.name, col))
    scored.sort(reverse=True)

    used_cols: set[str] = set()
    used_fields: set[str] = set()
    mappings: list[ColumnMap] = []
    for s, field, col in scored:
        if field in used_fields or col in used_cols:
            continue
        used_fields.add(field)
        used_cols.add(col)
        mappings.append(
            ColumnMap(
                target_field=field,
                source_column=col,
                transform=_guess_transform(field),
                confidence=round(s, 2),
                reasoning="heuristic match (offline, no LLM)",
            )
        )

    unmapped = [c for c in columns if c not in used_cols]
    return MappingPlan(mappings=mappings, unmapped_columns=unmapped)
