"""Run a mandate against a persisted upload, end to end through the DB."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models
from app.db.database import Base
from app.extraction import extract
from app.schemas.evaluation import ConstraintId
from app.schemas.fund import Fund
from app.schemas.mandate import MandateSpec
from app.services.evaluation import create_mandate, run_mandate, serialize_run
from app.services.persistence import save_extraction

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2024, 1, 1)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def run_out(db):
    raw = (FIXTURES / "messy_universe.csv").read_bytes()
    upload = save_extraction(db, [extract(raw, "messy_universe.csv", Fund)])
    spec = MandateSpec(
        max_redemption_frequency="quarterly",  # all funds are monthly/quarterly
        max_notice_period_days=60,             # Delta (90d) -> hard fail
        excluded_strategies=["managed_futures"],  # Cobalt -> hard fail
        max_management_fee=0.018,              # Alpha/Echo (2%) -> soft -10
        preferred_strategies=["global_macro"],  # only Alpha preferred
        min_aum_usd=100_000_000,               # Echo AUM withheld -> na
    )
    mandate = create_mandate(db, spec)
    run = run_mandate(db, upload.id, mandate, today=TODAY)
    return serialize_run(run)


def test_one_evaluation_per_fund(db, run_out):
    assert len(run_out.evaluations) == 5
    persisted = list(db.scalars(select(models.FundEvaluation)))
    assert len(persisted) == 5


def test_ranking_passed_first_then_score(run_out):
    names = [e.fund_name for e in run_out.evaluations]
    passed = [e for e in run_out.evaluations if e.passed]
    failed = [e for e in run_out.evaluations if not e.passed]
    # passed funds come first
    assert names[: len(passed)] == [e.fund_name for e in passed]
    # passed funds are score-sorted descending
    scores = [e.score for e in passed]
    assert scores == sorted(scores, reverse=True)
    # Alpha tops it (only soft mgmt-fee hit): 90
    assert run_out.evaluations[0].fund_name == "Alpha Macro Partners"
    assert run_out.evaluations[0].score == pytest.approx(90.0)
    assert {e.fund_name for e in failed} == {
        "Cobalt Managed Futures",
        "Delta Credit Opportunities",
    }


def test_hard_violations_recorded(run_out):
    cobalt = next(e for e in run_out.evaluations if e.fund_name.startswith("Cobalt"))
    assert cobalt.passed is False
    assert any(
        c.constraint == ConstraintId.EXCLUDED_STRATEGY and c.status.value == "fail"
        for c in cobalt.checks
    )


def test_na_for_missing_data(run_out):
    echo = next(e for e in run_out.evaluations if e.fund_name.startswith("Echo"))
    aum_check = next(c for c in echo.checks if c.constraint == ConstraintId.MIN_AUM)
    assert aum_check.status.value == "na"  # AUM was withheld in the source
