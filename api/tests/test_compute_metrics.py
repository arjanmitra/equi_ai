"""Compute pipeline: returns + benchmark + risk-free -> FundMetrics (hermetic)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models
from app.db.database import Base
from app.extraction import extract
from app.market.benchmarks import benchmark_for
from app.schemas.evaluation import CheckStatus, ConstraintId
from app.schemas.fund import Fund
from app.schemas.mandate import MandateSpec
from app.services.evaluation import create_mandate, run_mandate, serialize_run
from app.services.metrics import compute_metrics_for_upload
from app.services.persistence import save_extraction
from app.services.returns import ingest_returns_for_upload

FIXTURES = Path(__file__).parent / "fixtures"


def test_benchmark_mapping_and_override():
    assert benchmark_for("global_macro")[0] == "SPY"
    assert benchmark_for("credit")[0] == "AGG"
    # weak-fit strategies carry a note
    assert benchmark_for("managed_futures")[1] is not None
    assert benchmark_for("long_short_equity")[1] is None
    # override wins and clears the note
    assert benchmark_for("global_macro", {"global_macro": "QQQ"}) == ("QQQ", None)


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
def upload(db):
    raw = (FIXTURES / "messy_universe.csv").read_bytes()
    up = save_extraction(db, [extract(raw, "messy_universe.csv", Fund)])
    returns = (FIXTURES / "returns_long.csv").read_bytes()
    ingest_returns_for_upload(db, up.id, returns, "returns_long.csv")  # Alpha(3), Beacon(2)
    return up


def _by_name(db, name):
    return next(f for f in db.scalars(select(models.Fund)) if f.name == name)


def test_metrics_computed_for_funds_with_returns(db, upload):
    compute_metrics_for_upload(db, upload.id)

    alpha = _by_name(db, "Alpha Macro Partners").metrics
    assert alpha is not None
    assert alpha.n_obs == 3
    assert alpha.annualized_volatility is not None
    assert alpha.max_drawdown is not None
    assert alpha.sharpe is not None
    assert alpha.correlation_benchmark is not None
    assert alpha.benchmark_ticker == "SPY"  # global_macro -> SPY
    assert alpha.low_confidence is True  # 3 < MIN_OBS


def test_funds_without_returns_have_empty_metrics(db, upload):
    compute_metrics_for_upload(db, upload.id)
    cobalt = _by_name(db, "Cobalt Managed Futures").metrics
    assert cobalt is not None
    assert cobalt.n_obs == 0
    assert cobalt.annualized_volatility is None
    assert cobalt.sharpe is None


def test_credit_fund_maps_to_agg(db, upload):
    compute_metrics_for_upload(db, upload.id)
    delta = _by_name(db, "Delta Credit Opportunities").metrics
    assert delta.benchmark_ticker == "AGG"  # credit -> AGG


def test_override_changes_benchmark(db, upload):
    compute_metrics_for_upload(db, upload.id, overrides={"global_macro": "QQQ"})
    alpha = _by_name(db, "Alpha Macro Partners").metrics
    assert alpha.benchmark_ticker == "QQQ"


def test_inputs_json_records_audit_basis(db, upload):
    compute_metrics_for_upload(db, upload.id)
    alpha = _by_name(db, "Alpha Macro Partners").metrics
    inp = alpha.inputs_json
    assert inp["benchmark_ticker"] == "SPY"
    assert inp["risk_free_ticker"] == "DGS3MO"
    assert inp["rf_annual"] is not None
    assert inp["aligned_months"] == 3


def test_compute_is_idempotent(db, upload):
    compute_metrics_for_upload(db, upload.id)
    compute_metrics_for_upload(db, upload.id)
    rows = list(db.scalars(select(models.FundMetrics)))
    assert len(rows) == 5  # one per fund, not duplicated


def test_run_consumes_metrics_and_surfaces_sharpe(db, upload):
    compute_metrics_for_upload(db, upload.id)
    mandate = create_mandate(db, MandateSpec(target_volatility=0.10))
    out = serialize_run(run_mandate(db, upload.id, mandate))

    alpha = next(e for e in out.evaluations if e.fund_name.startswith("Alpha"))
    assert alpha.sharpe is not None  # surfaced from FundMetrics

    vol_check = next(
        c for c in alpha.checks if c.constraint == ConstraintId.TARGET_VOLATILITY
    )
    # 3 months -> low-confidence -> the risk check is na, fund not eliminated.
    assert vol_check.status == CheckStatus.NA
    assert "low-confidence" in vol_check.reason
    assert alpha.passed is True


def test_risk_constraint_eliminates_live_with_enough_history(db):
    # Fresh upload with 12 months of Alpha returns (alt. +/-5% -> ~18% vol).
    raw = (FIXTURES / "messy_universe.csv").read_bytes()
    up = save_extraction(db, [extract(raw, "messy_universe.csv", Fund)])
    returns = (FIXTURES / "returns_alpha_12mo.csv").read_bytes()
    ingest_returns_for_upload(db, up.id, returns, "returns_alpha_12mo.csv")
    compute_metrics_for_upload(db, up.id)

    alpha_metrics = _by_name(db, "Alpha Macro Partners").metrics
    assert alpha_metrics.n_obs == 12
    assert alpha_metrics.low_confidence is False  # exactly MIN_OBS

    # A 5% vol target against ~18% realized vol -> live HARD fail.
    mandate = create_mandate(db, MandateSpec(target_volatility=0.05))
    out = serialize_run(run_mandate(db, up.id, mandate))
    alpha = next(e for e in out.evaluations if e.fund_name.startswith("Alpha"))
    vol_check = next(
        c for c in alpha.checks if c.constraint == ConstraintId.TARGET_VOLATILITY
    )
    assert vol_check.status == CheckStatus.FAIL
    assert alpha.passed is False
