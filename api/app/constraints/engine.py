"""Deterministic mandate constraint engine.

    evaluate(fund, mandate) -> FundEvaluation

No LLM — this is pure spine. Each constraint is a small function returning a
ConstraintCheck (or None if the mandate doesn't specify it). Hard violations
eliminate a fund; soft violations subtract a fixed penalty from a 100-point
score; anything that can't be judged (missing fund data, or the risk metrics
that don't exist yet) is reported `na` and never penalized — "missing != wrong".

The engine reads attributes by name, so it works on either the ORM `Fund` or the
Pydantic `Fund` (same field names). Strategy/redemption values are compared as
their string forms, which both representations already use.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Protocol

from app.schemas.evaluation import (
    CheckStatus,
    ConstraintCheck,
    ConstraintId,
    FundEvaluation,
    Severity,
)
from app.schemas.mandate import MandateSpec

# Lower = more liquid. Used to compare a fund's redemption frequency against the
# least-liquid frequency the mandate will accept.
_REDEMPTION_ORDER = {
    "daily": 0,
    "weekly": 1,
    "monthly": 2,
    "quarterly": 3,
    "semi_annual": 4,
    "annual": 5,
}

# Fixed soft-violation penalties (out of 100). Magnitude-scaling is a future
# refinement; fixed weights keep the score transparent and testable.
_PENALTY = {
    ConstraintId.PREFERRED_STRATEGY: 15.0,
    ConstraintId.MANAGEMENT_FEE: 10.0,
    ConstraintId.PERFORMANCE_FEE: 10.0,
    ConstraintId.MIN_AUM: 10.0,
    ConstraintId.MIN_TRACK_RECORD: 10.0,
}


class FundView(Protocol):
    strategy: str | None
    redemption_frequency: str | None
    notice_period_days: int | None
    lockup_months: int | None
    management_fee: float | None
    performance_fee: float | None
    aum_usd: float | None
    inception_date: date | None


def _sval(v) -> str | None:
    return v.value if isinstance(v, Enum) else v


def _na(cid: ConstraintId, sev: Severity, reason: str, fields: list[str], **kw) -> ConstraintCheck:
    return ConstraintCheck(
        constraint=cid, severity=sev, status=CheckStatus.NA, reason=reason,
        source_fields=fields, **kw,
    )


# --- Liquidity (HARD) -------------------------------------------------------
def _check_redemption(fund: FundView, m: MandateSpec) -> ConstraintCheck | None:
    if m.max_redemption_frequency is None:
        return None
    thr = _sval(m.max_redemption_frequency)
    actual = fund.redemption_frequency
    fields = ["redemption_frequency"]
    if actual not in _REDEMPTION_ORDER or thr not in _REDEMPTION_ORDER:
        return _na(ConstraintId.REDEMPTION_FREQUENCY, Severity.HARD,
                   "fund redemption frequency unknown", fields,
                   actual=actual, threshold=thr)
    ok = _REDEMPTION_ORDER[actual] <= _REDEMPTION_ORDER[thr]
    return ConstraintCheck(
        constraint=ConstraintId.REDEMPTION_FREQUENCY, severity=Severity.HARD,
        status=CheckStatus.PASS if ok else CheckStatus.FAIL,
        actual=actual, threshold=thr, source_fields=fields,
        reason=(f"{actual} liquidity meets the {thr} requirement" if ok
                else f"{actual} liquidity is worse than the required {thr}"),
    )


def _check_notice(fund: FundView, m: MandateSpec) -> ConstraintCheck | None:
    if m.max_notice_period_days is None:
        return None
    actual, thr, fields = fund.notice_period_days, m.max_notice_period_days, ["notice_period_days"]
    if actual is None:
        return _na(ConstraintId.NOTICE_PERIOD, Severity.HARD,
                   "notice period unknown", fields, threshold=thr)
    ok = actual <= thr
    return ConstraintCheck(
        constraint=ConstraintId.NOTICE_PERIOD, severity=Severity.HARD,
        status=CheckStatus.PASS if ok else CheckStatus.FAIL,
        actual=actual, threshold=thr, source_fields=fields,
        reason=(f"{actual}-day notice within the {thr}-day limit" if ok
                else f"{actual}-day notice exceeds the {thr}-day limit"),
    )


def _check_lockup(fund: FundView, m: MandateSpec) -> ConstraintCheck | None:
    if m.max_lockup_months is None:
        return None
    actual, thr, fields = fund.lockup_months, m.max_lockup_months, ["lockup_months"]
    if actual is None:
        return _na(ConstraintId.LOCKUP, Severity.HARD, "lockup unknown", fields, threshold=thr)
    ok = actual <= thr
    return ConstraintCheck(
        constraint=ConstraintId.LOCKUP, severity=Severity.HARD,
        status=CheckStatus.PASS if ok else CheckStatus.FAIL,
        actual=actual, threshold=thr, source_fields=fields,
        reason=(f"{actual}-month lockup within the {thr}-month limit" if ok
                else f"{actual}-month lockup exceeds the {thr}-month limit"),
    )


# --- Strategy (excluded HARD, preferred SOFT) -------------------------------
def _check_excluded(fund: FundView, m: MandateSpec) -> ConstraintCheck | None:
    if not m.excluded_strategies:
        return None
    excluded = {_sval(s) for s in m.excluded_strategies}
    actual, fields = fund.strategy, ["strategy"]
    if actual is None:
        return _na(ConstraintId.EXCLUDED_STRATEGY, Severity.HARD,
                   "strategy unknown", fields)
    bad = actual in excluded
    return ConstraintCheck(
        constraint=ConstraintId.EXCLUDED_STRATEGY, severity=Severity.HARD,
        status=CheckStatus.FAIL if bad else CheckStatus.PASS,
        actual=actual, threshold=sorted(excluded), source_fields=fields,
        reason=(f"strategy '{actual}' is excluded by the mandate" if bad
                else f"strategy '{actual}' is not on the exclusion list"),
    )


def _check_preferred(fund: FundView, m: MandateSpec) -> ConstraintCheck | None:
    if not m.preferred_strategies:
        return None
    preferred = {_sval(s) for s in m.preferred_strategies}
    actual, fields = fund.strategy, ["strategy"]
    if actual is None:
        return _na(ConstraintId.PREFERRED_STRATEGY, Severity.SOFT,
                   "strategy unknown", fields)
    ok = actual in preferred
    return ConstraintCheck(
        constraint=ConstraintId.PREFERRED_STRATEGY, severity=Severity.SOFT,
        status=CheckStatus.PASS if ok else CheckStatus.FAIL,
        penalty=0.0 if ok else _PENALTY[ConstraintId.PREFERRED_STRATEGY],
        actual=actual, threshold=sorted(preferred), source_fields=fields,
        reason=(f"strategy '{actual}' is in the preferred set" if ok
                else f"strategy '{actual}' is outside the preferred set"),
    )


# --- Fees (SOFT) ------------------------------------------------------------
def _check_fee(fund: FundView, m: MandateSpec, cid: ConstraintId) -> ConstraintCheck | None:
    if cid is ConstraintId.MANAGEMENT_FEE:
        thr, actual, field, label = m.max_management_fee, fund.management_fee, "management_fee", "management fee"
    else:
        thr, actual, field, label = m.max_performance_fee, fund.performance_fee, "performance_fee", "performance fee"
    if thr is None:
        return None
    if actual is None:
        return _na(cid, Severity.SOFT, f"{label} unknown", [field], threshold=thr)
    ok = actual <= thr
    return ConstraintCheck(
        constraint=cid, severity=Severity.SOFT,
        status=CheckStatus.PASS if ok else CheckStatus.FAIL,
        penalty=0.0 if ok else _PENALTY[cid],
        actual=actual, threshold=thr, source_fields=[field],
        reason=(f"{label} {actual:.2%} within the {thr:.2%} ceiling" if ok
                else f"{label} {actual:.2%} exceeds the {thr:.2%} ceiling"),
    )


# --- Size / track record (SOFT) ---------------------------------------------
def _check_min_aum(fund: FundView, m: MandateSpec) -> ConstraintCheck | None:
    if m.min_aum_usd is None:
        return None
    actual, thr, fields = fund.aum_usd, m.min_aum_usd, ["aum_usd"]
    if actual is None:
        return _na(ConstraintId.MIN_AUM, Severity.SOFT, "AUM unknown", fields, threshold=thr)
    ok = actual >= thr
    return ConstraintCheck(
        constraint=ConstraintId.MIN_AUM, severity=Severity.SOFT,
        status=CheckStatus.PASS if ok else CheckStatus.FAIL,
        penalty=0.0 if ok else _PENALTY[ConstraintId.MIN_AUM],
        actual=actual, threshold=thr, source_fields=fields,
        reason=(f"AUM ${actual:,.0f} meets the ${thr:,.0f} minimum" if ok
                else f"AUM ${actual:,.0f} is below the ${thr:,.0f} minimum"),
    )


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def _check_track_record(fund: FundView, m: MandateSpec, today: date) -> ConstraintCheck | None:
    if m.min_track_record_months is None:
        return None
    thr, fields = m.min_track_record_months, ["inception_date"]
    if fund.inception_date is None:
        return _na(ConstraintId.MIN_TRACK_RECORD, Severity.SOFT,
                   "inception date unknown", fields, threshold=thr)
    months = _months_between(fund.inception_date, today)
    ok = months >= thr
    return ConstraintCheck(
        constraint=ConstraintId.MIN_TRACK_RECORD, severity=Severity.SOFT,
        status=CheckStatus.PASS if ok else CheckStatus.FAIL,
        penalty=0.0 if ok else _PENALTY[ConstraintId.MIN_TRACK_RECORD],
        actual=months, threshold=thr, source_fields=fields,
        reason=(f"{months}-month track record meets the {thr}-month minimum" if ok
                else f"{months}-month track record is below the {thr}-month minimum"),
    )


# --- Risk (deferred until metrics exist) ------------------------------------
def _check_risk_deferred(m: MandateSpec) -> list[ConstraintCheck]:
    out: list[ConstraintCheck] = []
    if m.target_volatility is not None:
        out.append(_na(ConstraintId.TARGET_VOLATILITY, Severity.HARD,
                       "pending metrics (volatility not yet computed)", [],
                       threshold=m.target_volatility))
    if m.max_drawdown is not None:
        out.append(_na(ConstraintId.MAX_DRAWDOWN, Severity.HARD,
                       "pending metrics (drawdown not yet computed)", [],
                       threshold=m.max_drawdown))
    return out


def evaluate(fund: FundView, mandate: MandateSpec, today: date | None = None) -> FundEvaluation:
    today = today or date.today()

    maybe = [
        _check_redemption(fund, mandate),
        _check_notice(fund, mandate),
        _check_lockup(fund, mandate),
        _check_excluded(fund, mandate),
        _check_preferred(fund, mandate),
        _check_fee(fund, mandate, ConstraintId.MANAGEMENT_FEE),
        _check_fee(fund, mandate, ConstraintId.PERFORMANCE_FEE),
        _check_min_aum(fund, mandate),
        _check_track_record(fund, mandate, today),
    ]
    checks = [c for c in maybe if c is not None] + _check_risk_deferred(mandate)

    passed = not any(
        c.severity is Severity.HARD and c.status is CheckStatus.FAIL for c in checks
    )
    score = max(0.0, min(100.0, 100.0 - sum(c.penalty for c in checks)))
    return FundEvaluation(passed=passed, score=score, checks=checks)
