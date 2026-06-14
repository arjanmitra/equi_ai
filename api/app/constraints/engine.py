"""Deterministic mandate constraint engine.

    evaluate(fund, mandate) -> FundEvaluation

No LLM — this is pure mechanism. Each constraint is a small function returning a
ConstraintCheck (or None if the mandate doesn't specify it).

Severity and penalty are POLICY, owned by the mandate, not the engine: each
constraint resolves its severity (hard / soft) and soft-penalty from the
mandate's optional override maps, falling back to the defaults below. A hard
violation eliminates a fund; a soft violation subtracts its penalty from a
100-point score; anything that can't be judged (missing fund data, or risk
metrics that are low-confidence / not yet computed) is reported `na` and never
eliminates or penalizes — "missing != wrong", regardless of severity.

The engine reads attributes by name, so it works on either the ORM `Fund` or the
Pydantic `Fund` (same field names).
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
from app.schemas.mandate import CustomConstraint, MandateSpec

# Lower = more liquid. Compares a fund's redemption frequency against the
# least-liquid frequency the mandate will accept.
_REDEMPTION_ORDER = {
    "daily": 0, "weekly": 1, "monthly": 2, "quarterly": 3, "semi_annual": 4, "annual": 5,
}

# Default severity per constraint (overridable per-mandate).
DEFAULT_SEVERITY: dict[ConstraintId, Severity] = {
    ConstraintId.REDEMPTION_FREQUENCY: Severity.HARD,
    ConstraintId.NOTICE_PERIOD: Severity.HARD,
    ConstraintId.LOCKUP: Severity.HARD,
    ConstraintId.EXCLUDED_STRATEGY: Severity.HARD,
    ConstraintId.TARGET_VOLATILITY: Severity.HARD,
    ConstraintId.MAX_DRAWDOWN: Severity.HARD,
    ConstraintId.PREFERRED_STRATEGY: Severity.SOFT,
    ConstraintId.MANAGEMENT_FEE: Severity.SOFT,
    ConstraintId.PERFORMANCE_FEE: Severity.SOFT,
    ConstraintId.MIN_AUM: Severity.SOFT,
    ConstraintId.MIN_TRACK_RECORD: Severity.SOFT,
}

# Default soft-penalty per constraint (out of 100), overridable per-mandate.
# The normally-hard constraints carry a higher default, used only if the user
# softens them.
DEFAULT_PENALTY: dict[ConstraintId, float] = {
    ConstraintId.PREFERRED_STRATEGY: 15.0,
    ConstraintId.MANAGEMENT_FEE: 10.0,
    ConstraintId.PERFORMANCE_FEE: 10.0,
    ConstraintId.MIN_AUM: 10.0,
    ConstraintId.MIN_TRACK_RECORD: 10.0,
    ConstraintId.REDEMPTION_FREQUENCY: 25.0,
    ConstraintId.NOTICE_PERIOD: 25.0,
    ConstraintId.LOCKUP: 25.0,
    ConstraintId.EXCLUDED_STRATEGY: 25.0,
    ConstraintId.TARGET_VOLATILITY: 25.0,
    ConstraintId.MAX_DRAWDOWN: 25.0,
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


def _resolve(m: MandateSpec, cid: ConstraintId) -> tuple[Severity, float]:
    """Severity + soft-penalty for this constraint, from the mandate or defaults."""
    sev_str = (m.severities or {}).get(cid.value)
    severity = Severity(sev_str) if sev_str in ("hard", "soft") else DEFAULT_SEVERITY[cid]
    penalty = float((m.penalties or {}).get(cid.value, DEFAULT_PENALTY[cid]))
    return severity, penalty


def _na(cid: ConstraintId, sev: Severity, reason: str, fields: list[str], **kw) -> ConstraintCheck:
    return ConstraintCheck(
        constraint=cid, severity=sev, status=CheckStatus.NA, reason=reason,
        source_fields=fields, **kw,
    )


def _verdict(
    cid: ConstraintId, sev: Severity, pen: float, ok: bool, *,
    actual, threshold, fields: list[str], reason: str,
) -> ConstraintCheck:
    return ConstraintCheck(
        constraint=cid, severity=sev,
        status=CheckStatus.PASS if ok else CheckStatus.FAIL,
        penalty=pen if (sev is Severity.SOFT and not ok) else 0.0,
        actual=actual, threshold=threshold, source_fields=fields, reason=reason,
    )


# --- Liquidity --------------------------------------------------------------
def _check_redemption(fund: FundView, m: MandateSpec) -> ConstraintCheck | None:
    if m.max_redemption_frequency is None:
        return None
    sev, pen = _resolve(m, ConstraintId.REDEMPTION_FREQUENCY)
    thr, actual, fields = _sval(m.max_redemption_frequency), fund.redemption_frequency, ["redemption_frequency"]
    if actual not in _REDEMPTION_ORDER or thr not in _REDEMPTION_ORDER:
        return _na(ConstraintId.REDEMPTION_FREQUENCY, sev,
                   "fund redemption frequency unknown", fields, actual=actual, threshold=thr)
    ok = _REDEMPTION_ORDER[actual] <= _REDEMPTION_ORDER[thr]
    return _verdict(ConstraintId.REDEMPTION_FREQUENCY, sev, pen, ok,
                    actual=actual, threshold=thr, fields=fields,
                    reason=(f"{actual} liquidity meets the {thr} requirement" if ok
                            else f"{actual} liquidity is worse than the required {thr}"))


def _check_notice(fund: FundView, m: MandateSpec) -> ConstraintCheck | None:
    if m.max_notice_period_days is None:
        return None
    sev, pen = _resolve(m, ConstraintId.NOTICE_PERIOD)
    actual, thr, fields = fund.notice_period_days, m.max_notice_period_days, ["notice_period_days"]
    if actual is None:
        return _na(ConstraintId.NOTICE_PERIOD, sev, "notice period unknown", fields, threshold=thr)
    ok = actual <= thr
    return _verdict(ConstraintId.NOTICE_PERIOD, sev, pen, ok,
                    actual=actual, threshold=thr, fields=fields,
                    reason=(f"{actual}-day notice within the {thr}-day limit" if ok
                            else f"{actual}-day notice exceeds the {thr}-day limit"))


def _check_lockup(fund: FundView, m: MandateSpec) -> ConstraintCheck | None:
    if m.max_lockup_months is None:
        return None
    sev, pen = _resolve(m, ConstraintId.LOCKUP)
    actual, thr, fields = fund.lockup_months, m.max_lockup_months, ["lockup_months"]
    if actual is None:
        return _na(ConstraintId.LOCKUP, sev, "lockup unknown", fields, threshold=thr)
    ok = actual <= thr
    return _verdict(ConstraintId.LOCKUP, sev, pen, ok,
                    actual=actual, threshold=thr, fields=fields,
                    reason=(f"{actual}-month lockup within the {thr}-month limit" if ok
                            else f"{actual}-month lockup exceeds the {thr}-month limit"))


# --- Strategy ---------------------------------------------------------------
def _check_excluded(fund: FundView, m: MandateSpec) -> ConstraintCheck | None:
    if not m.excluded_strategies:
        return None
    sev, pen = _resolve(m, ConstraintId.EXCLUDED_STRATEGY)
    excluded = {_sval(s) for s in m.excluded_strategies}
    actual, fields = fund.strategy, ["strategy"]
    if actual is None:
        return _na(ConstraintId.EXCLUDED_STRATEGY, sev, "strategy unknown", fields)
    bad = actual in excluded
    return _verdict(ConstraintId.EXCLUDED_STRATEGY, sev, pen, not bad,
                    actual=actual, threshold=sorted(excluded), fields=fields,
                    reason=(f"strategy '{actual}' is excluded by the mandate" if bad
                            else f"strategy '{actual}' is not on the exclusion list"))


def _check_preferred(fund: FundView, m: MandateSpec) -> ConstraintCheck | None:
    if not m.preferred_strategies:
        return None
    sev, pen = _resolve(m, ConstraintId.PREFERRED_STRATEGY)
    preferred = {_sval(s) for s in m.preferred_strategies}
    actual, fields = fund.strategy, ["strategy"]
    if actual is None:
        return _na(ConstraintId.PREFERRED_STRATEGY, sev, "strategy unknown", fields)
    ok = actual in preferred
    return _verdict(ConstraintId.PREFERRED_STRATEGY, sev, pen, ok,
                    actual=actual, threshold=sorted(preferred), fields=fields,
                    reason=(f"strategy '{actual}' is in the preferred set" if ok
                            else f"strategy '{actual}' is outside the preferred set"))


# --- Fees -------------------------------------------------------------------
def _check_fee(fund: FundView, m: MandateSpec, cid: ConstraintId) -> ConstraintCheck | None:
    if cid is ConstraintId.MANAGEMENT_FEE:
        thr, actual, field, label = m.max_management_fee, fund.management_fee, "management_fee", "management fee"
    else:
        thr, actual, field, label = m.max_performance_fee, fund.performance_fee, "performance_fee", "performance fee"
    if thr is None:
        return None
    sev, pen = _resolve(m, cid)
    if actual is None:
        return _na(cid, sev, f"{label} unknown", [field], threshold=thr)
    ok = actual <= thr
    return _verdict(cid, sev, pen, ok, actual=actual, threshold=thr, fields=[field],
                    reason=(f"{label} {actual:.2%} within the {thr:.2%} ceiling" if ok
                            else f"{label} {actual:.2%} exceeds the {thr:.2%} ceiling"))


# --- Size / track record ----------------------------------------------------
def _check_min_aum(fund: FundView, m: MandateSpec) -> ConstraintCheck | None:
    if m.min_aum_usd is None:
        return None
    sev, pen = _resolve(m, ConstraintId.MIN_AUM)
    actual, thr, fields = fund.aum_usd, m.min_aum_usd, ["aum_usd"]
    if actual is None:
        return _na(ConstraintId.MIN_AUM, sev, "AUM unknown", fields, threshold=thr)
    ok = actual >= thr
    return _verdict(ConstraintId.MIN_AUM, sev, pen, ok, actual=actual, threshold=thr, fields=fields,
                    reason=(f"AUM ${actual:,.0f} meets the ${thr:,.0f} minimum" if ok
                            else f"AUM ${actual:,.0f} is below the ${thr:,.0f} minimum"))


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def _check_track_record(fund: FundView, m: MandateSpec, today: date) -> ConstraintCheck | None:
    if m.min_track_record_months is None:
        return None
    sev, pen = _resolve(m, ConstraintId.MIN_TRACK_RECORD)
    thr, fields = m.min_track_record_months, ["inception_date"]
    if fund.inception_date is None:
        return _na(ConstraintId.MIN_TRACK_RECORD, sev, "inception date unknown", fields, threshold=thr)
    months = _months_between(fund.inception_date, today)
    ok = months >= thr
    return _verdict(ConstraintId.MIN_TRACK_RECORD, sev, pen, ok, actual=months, threshold=thr, fields=fields,
                    reason=(f"{months}-month track record meets the {thr}-month minimum" if ok
                            else f"{months}-month track record is below the {thr}-month minimum"))


# --- Risk (evaluated against computed metrics, else na) ---------------------
def _check_target_vol(mandate: MandateSpec, metrics) -> ConstraintCheck | None:
    if mandate.target_volatility is None:
        return None
    sev, pen = _resolve(mandate, ConstraintId.TARGET_VOLATILITY)
    thr, fields = mandate.target_volatility, ["annualized_volatility"]
    vol = getattr(metrics, "annualized_volatility", None) if metrics else None
    if vol is None:
        return _na(ConstraintId.TARGET_VOLATILITY, sev,
                   "pending metrics (volatility not computed)", fields, threshold=thr)
    if getattr(metrics, "low_confidence", False):
        return _na(ConstraintId.TARGET_VOLATILITY, sev,
                   f"volatility {vol:.1%} is low-confidence (n<12) — not enforced",
                   fields, actual=vol, threshold=thr)
    ok = vol <= thr
    return _verdict(ConstraintId.TARGET_VOLATILITY, sev, pen, ok, actual=vol, threshold=thr, fields=fields,
                    reason=(f"volatility {vol:.1%} within the {thr:.1%} target" if ok
                            else f"volatility {vol:.1%} exceeds the {thr:.1%} target"))


def _check_max_dd(mandate: MandateSpec, metrics) -> ConstraintCheck | None:
    if mandate.max_drawdown is None:
        return None
    sev, pen = _resolve(mandate, ConstraintId.MAX_DRAWDOWN)
    tol, fields = mandate.max_drawdown, ["max_drawdown"]
    mdd = getattr(metrics, "max_drawdown", None) if metrics else None
    if mdd is None:
        return _na(ConstraintId.MAX_DRAWDOWN, sev,
                   "pending metrics (drawdown not computed)", fields, threshold=tol)
    if getattr(metrics, "low_confidence", False):
        return _na(ConstraintId.MAX_DRAWDOWN, sev,
                   f"drawdown {mdd:.1%} is low-confidence (n<12) — not enforced",
                   fields, actual=mdd, threshold=tol)
    ok = abs(mdd) <= tol
    return _verdict(ConstraintId.MAX_DRAWDOWN, sev, pen, ok, actual=mdd, threshold=tol, fields=fields,
                    reason=(f"max drawdown {mdd:.1%} within the {tol:.1%} tolerance" if ok
                            else f"max drawdown {abs(mdd):.1%} exceeds the {tol:.1%} tolerance"))


# --- Promoted attributes (generic, user-defined rules) ----------------------
_OP_TEXT = {
    "gte": "≥", "lte": "≤", "gt": ">", "lt": "<", "eq": "=", "neq": "≠",
    "contains": "contains",
}


def _to_number(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("$", "").replace("%", "")
    try:
        return float(s)
    except ValueError:
        return None


def _apply_number(op: str, a: float, b: float) -> bool:
    return {
        "gte": a >= b, "lte": a <= b, "gt": a > b, "lt": a < b,
        "eq": a == b, "neq": a != b, "contains": str(b) in str(a),
    }[op]


def _apply_text(op: str, a: str, b: str) -> bool:
    a, b = a.strip().lower(), b.strip().lower()
    return {"eq": a == b, "neq": a != b, "contains": b in a}.get(op, False)


def _check_custom(cc: CustomConstraint, attributes: dict[str, str]) -> ConstraintCheck:
    """Judge one promoted-attribute rule. Untrusted source: the reason always
    says 'reported', and a missing/uncoercible value is na (never a failure)."""
    sev = Severity(cc.severity)
    fields = [f"attribute: {cc.attribute}"]
    raw = attributes.get(cc.attribute)
    op_txt = _OP_TEXT.get(cc.operator, cc.operator)

    if raw is None or str(raw).strip() == "":
        return ConstraintCheck(
            constraint=cc.id, severity=sev, status=CheckStatus.NA,
            threshold=cc.threshold, source_fields=fields,
            reason=f"reported {cc.label} not available for this fund",
        )

    if cc.value_type == "number":
        actual = _to_number(raw)
        thr = _to_number(cc.threshold)
        if actual is None or thr is None:
            return ConstraintCheck(
                constraint=cc.id, severity=sev, status=CheckStatus.NA,
                actual=raw, threshold=cc.threshold, source_fields=fields,
                reason=f"reported {cc.label} '{raw}' is not numeric — not enforced",
            )
        ok = _apply_number(cc.operator, actual, thr)
        actual_disp, thr_disp = actual, thr
    else:
        ok = _apply_text(cc.operator, str(raw), str(cc.threshold))
        actual_disp, thr_disp = raw, cc.threshold

    return ConstraintCheck(
        constraint=cc.id, severity=sev,
        status=CheckStatus.PASS if ok else CheckStatus.FAIL,
        penalty=float(cc.penalty) if (sev is Severity.SOFT and not ok) else 0.0,
        actual=actual_disp, threshold=thr_disp, source_fields=fields,
        reason=(
            f"reported {cc.label} {actual_disp} meets the rule ({op_txt} {thr_disp})"
            if ok else
            f"reported {cc.label} {actual_disp} fails the rule ({op_txt} {thr_disp})"
        ),
    )


def evaluate(
    fund: FundView,
    mandate: MandateSpec,
    metrics=None,
    today: date | None = None,
    attributes: dict[str, str] | None = None,
) -> FundEvaluation:
    today = today or date.today()
    attributes = attributes or {}

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
        _check_target_vol(mandate, metrics),
        _check_max_dd(mandate, metrics),
    ]
    checks = [c for c in maybe if c is not None]
    checks += [_check_custom(cc, attributes) for cc in mandate.custom_constraints]

    # `passed` = no hard violation. na never eliminates (missing != wrong). The
    # degenerate "every check is na" case (e.g. a fund whose data didn't extract)
    # is not treated as a failure here — it's surfaced as "not evaluated" at the
    # presentation layer (serialize_run / UI), which keeps it off the shortlist
    # without stamping it as failed.
    passed = not any(
        c.severity is Severity.HARD and c.status is CheckStatus.FAIL for c in checks
    )
    score = max(0.0, min(100.0, 100.0 - sum(c.penalty for c in checks)))
    return FundEvaluation(passed=passed, score=score, checks=checks)
