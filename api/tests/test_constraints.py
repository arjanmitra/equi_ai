"""Unit tests for the pure constraint engine — hard/soft/na, scoring, ordinals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from app.constraints import evaluate
from app.schemas.evaluation import CheckStatus, ConstraintId, Severity
from app.schemas.fund import Fund
from app.schemas.mandate import MandateSpec

TODAY = date(2024, 1, 1)


@dataclass
class StubMetrics:
    annualized_volatility: float | None = None
    max_drawdown: float | None = None
    low_confidence: bool = False


def make_fund(**over) -> Fund:
    base = dict(
        name="Test Fund",
        strategy="global_macro",
        redemption_frequency="monthly",
        notice_period_days=30,
        lockup_months=0,
        management_fee=0.015,
        performance_fee=0.15,
        aum_usd=500_000_000,
        inception_date=date(2015, 1, 1),
    )
    base.update(over)
    return Fund(**base)


def _check(ev, cid: ConstraintId):
    return next(c for c in ev.checks if c.constraint == cid)


def test_empty_mandate_passes_with_full_score():
    ev = evaluate(make_fund(), MandateSpec(), today=TODAY)
    assert ev.passed and ev.score == 100.0 and ev.checks == []


def test_excluded_strategy_is_hard_fail():
    m = MandateSpec(excluded_strategies=["global_macro"])
    ev = evaluate(make_fund(strategy="global_macro"), m, today=TODAY)
    assert ev.passed is False
    c = _check(ev, ConstraintId.EXCLUDED_STRATEGY)
    assert c.severity is Severity.HARD and c.status is CheckStatus.FAIL


def test_notice_period_hard_fail():
    m = MandateSpec(max_notice_period_days=30)
    ev = evaluate(make_fund(notice_period_days=90), m, today=TODAY)
    assert ev.passed is False
    assert _check(ev, ConstraintId.NOTICE_PERIOD).status is CheckStatus.FAIL


def test_redemption_ordinal_pass_and_fail():
    m = MandateSpec(max_redemption_frequency="quarterly")
    # monthly is more liquid than quarterly -> passes
    assert evaluate(make_fund(redemption_frequency="monthly"), m, today=TODAY).passed
    # annual is less liquid than quarterly -> hard fail
    ev = evaluate(make_fund(redemption_frequency="annual"), m, today=TODAY)
    assert ev.passed is False
    assert _check(ev, ConstraintId.REDEMPTION_FREQUENCY).status is CheckStatus.FAIL


def test_management_fee_is_soft_penalty_not_elimination():
    m = MandateSpec(max_management_fee=0.01)
    ev = evaluate(make_fund(management_fee=0.02), m, today=TODAY)
    assert ev.passed is True  # soft -> still passes
    c = _check(ev, ConstraintId.MANAGEMENT_FEE)
    assert c.severity is Severity.SOFT and c.status is CheckStatus.FAIL
    assert c.penalty == 10.0 and ev.score == 90.0


def test_preferred_strategy_miss_is_soft_penalty():
    m = MandateSpec(preferred_strategies=["credit"])
    ev = evaluate(make_fund(strategy="global_macro"), m, today=TODAY)
    assert ev.passed is True
    assert _check(ev, ConstraintId.PREFERRED_STRATEGY).penalty == 15.0
    assert ev.score == 85.0


def test_missing_data_is_na_and_unpenalized():
    m = MandateSpec(min_aum_usd=100_000_000)
    ev = evaluate(make_fund(aum_usd=None), m, today=TODAY)
    c = _check(ev, ConstraintId.MIN_AUM)
    assert c.status is CheckStatus.NA and c.penalty == 0.0
    assert ev.passed is True and ev.score == 100.0


def test_track_record_uses_today():
    m = MandateSpec(min_track_record_months=60)
    # inception 2015-01 vs today 2024-01 = 108 months -> pass
    assert evaluate(make_fund(inception_date=date(2015, 1, 1)), m, today=TODAY).passed
    # inception 2023-01 vs today 2024-01 = 12 months -> soft fail
    ev = evaluate(make_fund(inception_date=date(2023, 1, 1)), m, today=TODAY)
    c = _check(ev, ConstraintId.MIN_TRACK_RECORD)
    assert c.status is CheckStatus.FAIL and ev.score == 90.0


def test_risk_constraints_are_na_without_metrics():
    m = MandateSpec(target_volatility=0.1, max_drawdown=0.2)
    ev = evaluate(make_fund(), m, today=TODAY)  # metrics=None
    vol = _check(ev, ConstraintId.TARGET_VOLATILITY)
    assert vol.status is CheckStatus.NA and "pending metrics" in vol.reason
    assert ev.passed is True  # na never eliminates


def test_target_volatility_passes_within_limit():
    m = MandateSpec(target_volatility=0.10)
    metrics = StubMetrics(annualized_volatility=0.08)
    ev = evaluate(make_fund(), m, metrics=metrics, today=TODAY)
    c = _check(ev, ConstraintId.TARGET_VOLATILITY)
    assert c.severity is Severity.HARD and c.status is CheckStatus.PASS
    assert ev.passed is True


def test_target_volatility_hard_fails_when_exceeded():
    m = MandateSpec(target_volatility=0.10)
    ev = evaluate(make_fund(), m, metrics=StubMetrics(annualized_volatility=0.18), today=TODAY)
    assert _check(ev, ConstraintId.TARGET_VOLATILITY).status is CheckStatus.FAIL
    assert ev.passed is False


def test_max_drawdown_compares_magnitude():
    m = MandateSpec(max_drawdown=0.20)
    # -0.10 drawdown is within a 20% tolerance
    ok = evaluate(make_fund(), m, metrics=StubMetrics(max_drawdown=-0.10), today=TODAY)
    assert _check(ok, ConstraintId.MAX_DRAWDOWN).status is CheckStatus.PASS
    # -0.30 exceeds it -> hard fail
    bad = evaluate(make_fund(), m, metrics=StubMetrics(max_drawdown=-0.30), today=TODAY)
    assert _check(bad, ConstraintId.MAX_DRAWDOWN).status is CheckStatus.FAIL
    assert bad.passed is False


def test_low_confidence_metrics_are_not_enforced():
    m = MandateSpec(target_volatility=0.10)
    # Vol exceeds the target, but low-confidence -> na, not a hard fail.
    metrics = StubMetrics(annualized_volatility=0.40, low_confidence=True)
    ev = evaluate(make_fund(), m, metrics=metrics, today=TODAY)
    c = _check(ev, ConstraintId.TARGET_VOLATILITY)
    assert c.status is CheckStatus.NA and "low-confidence" in c.reason
    assert ev.passed is True


def test_score_clamps_and_sums_penalties():
    m = MandateSpec(
        preferred_strategies=["credit"],   # -15
        max_management_fee=0.01,           # -10
        max_performance_fee=0.01,          # -10
        min_aum_usd=10_000_000_000,        # -10
        min_track_record_months=600,       # -10  (total 55 -> 45)
    )
    ev = evaluate(make_fund(), m, today=TODAY)
    assert ev.passed is True and ev.score == pytest.approx(45.0)
