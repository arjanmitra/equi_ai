"""Promoted-attribute (custom) constraints — generic rules over the attribute bag.

Engine-level: number/text operators, severity, and the na-on-missing/uncoercible
guarantee. DB-level: a rule actually reads the captured attribute bag through a
real run and eliminates a fund on a manager-reported value.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.constraints import evaluate
from app.db.database import Base
from app.extraction import extract
from app.schemas.evaluation import CheckStatus, Severity
from app.schemas.fund import Fund
from app.schemas.mandate import CustomConstraint, MandateSpec
from app.services.evaluation import create_mandate, run_mandate
from app.services.persistence import save_extraction

TODAY = date(2024, 1, 1)
FIXTURES = Path(__file__).parent / "fixtures"


def _fund() -> Fund:
    return Fund(name="Test Fund", strategy="global_macro")


def _cc(**over) -> CustomConstraint:
    base = dict(id="custom:sortino", label="Sortino Ratio", attribute="Sortino", operator="gte", threshold=1.0)
    base.update(over)
    return CustomConstraint(**base)


def _check(ev, cid="custom:sortino"):
    return next(c for c in ev.checks if c.constraint == cid)


# --- engine: numeric -------------------------------------------------------

def test_number_rule_passes():
    m = MandateSpec(custom_constraints=[_cc()])
    ev = evaluate(_fund(), m, today=TODAY, attributes={"Sortino": "1.42"})
    assert _check(ev).status is CheckStatus.PASS
    assert ev.passed and ev.score == 100.0


def test_number_rule_soft_fail_penalizes_keeps_fund():
    m = MandateSpec(custom_constraints=[_cc(severity="soft", penalty=12.0)])
    ev = evaluate(_fund(), m, today=TODAY, attributes={"Sortino": "0.5"})
    c = _check(ev)
    assert c.status is CheckStatus.FAIL and c.penalty == 12.0
    assert ev.passed is True and ev.score == 88.0


def test_number_rule_hard_fail_eliminates():
    m = MandateSpec(custom_constraints=[_cc(severity="hard")])
    ev = evaluate(_fund(), m, today=TODAY, attributes={"Sortino": "0.5"})
    assert _check(ev).status is CheckStatus.FAIL
    assert ev.passed is False


def test_missing_attribute_is_na_not_fail():
    m = MandateSpec(custom_constraints=[_cc(severity="hard")])
    ev = evaluate(_fund(), m, today=TODAY, attributes={})  # fund has no such attribute
    assert _check(ev).status is CheckStatus.NA
    assert _check(ev).penalty == 0.0  # na never penalizes or eliminates
    assert ev.passed is True  # no hard violation; "not evaluated" is a UI concern


def test_non_numeric_value_is_na():
    m = MandateSpec(custom_constraints=[_cc(severity="hard")])
    ev = evaluate(_fund(), m, today=TODAY, attributes={"Sortino": "n/a"})
    assert _check(ev).status is CheckStatus.NA
    assert ev.passed is True


def test_reason_flags_reported():
    m = MandateSpec(custom_constraints=[_cc()])
    ev = evaluate(_fund(), m, today=TODAY, attributes={"Sortino": "1.42"})
    assert "reported" in _check(ev).reason.lower()
    assert _check(ev).source_fields == ["attribute: Sortino"]


# --- engine: text ----------------------------------------------------------

def test_text_contains_rule():
    cc = _cc(id="custom:esg", label="ESG", attribute="ESG", value_type="text", operator="contains", threshold="A")
    m = MandateSpec(custom_constraints=[cc])
    ev_a = evaluate(_fund(), m, today=TODAY, attributes={"ESG": "A-"})
    ev_b = evaluate(_fund(), m, today=TODAY, attributes={"ESG": "B"})
    assert _check(ev_a, "custom:esg").status is CheckStatus.PASS
    assert _check(ev_b, "custom:esg").status is CheckStatus.FAIL


# --- DB: reads the real captured attribute bag -----------------------------

@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_rule_reads_attribute_bag_through_a_run(db):
    # extra_columns_universe.csv carries "Sortino Ratio" 1.42 (Alpha) and 0.88 (Beacon)
    raw = (FIXTURES / "extra_columns_universe.csv").read_bytes()
    upload = save_extraction(db, [extract(raw, "extra_columns_universe.csv", Fund)])

    spec = MandateSpec(
        custom_constraints=[
            CustomConstraint(
                id="custom:sortino", label="Sortino Ratio",
                attribute="Sortino Ratio", operator="gte", threshold=1.0, severity="hard",
            )
        ]
    )
    mandate = create_mandate(db, spec)
    run = run_mandate(db, upload.id, mandate, today=TODAY)

    by_name = {ev.fund.name: ev for ev in run.evaluations}
    assert by_name["Alpha Macro Partners"].passed is True   # 1.42 >= 1.0
    assert by_name["Beacon L/S Equity"].passed is False     # 0.88 < 1.0 (hard)
    # the failing check names the source attribute
    beacon_checks = by_name["Beacon L/S Equity"].checks_json
    sortino = next(c for c in beacon_checks if c["constraint"] == "custom:sortino")
    assert sortino["status"] == "fail"
    assert sortino["source_fields"] == ["attribute: Sortino Ratio"]
