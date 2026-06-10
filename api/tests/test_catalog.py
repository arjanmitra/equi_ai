"""The grounding catalog: facts, stable IDs, provenance, ranking."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models
from app.db.database import Base
from app.extraction import extract
from app.memo import build_catalog, check_id, field_id, mandate_id, metric_id
from app.schemas.fund import Fund
from app.schemas.mandate import MandateSpec
from app.services.evaluation import create_mandate, run_mandate
from app.services.metrics import compute_metrics_for_upload
from app.services.persistence import save_extraction
from app.services.returns import ingest_returns_for_upload

FIXTURES = Path(__file__).parent / "fixtures"


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
def catalog(db):
    up = save_extraction(
        db, [extract((FIXTURES / "messy_universe.csv").read_bytes(), "u.csv", Fund)]
    )
    ingest_returns_for_upload(
        db, up.id, (FIXTURES / "returns_long.csv").read_bytes(), "r.csv"
    )
    compute_metrics_for_upload(db, up.id)
    mandate = create_mandate(
        db,
        MandateSpec(
            max_management_fee=0.018,
            max_redemption_frequency="quarterly",
            excluded_strategies=["managed_futures"],
        ),
    )
    run = run_mandate(db, up.id, mandate)
    return build_catalog(run)


def _fund_id(db, name):
    return next(f for f in db.scalars(select(models.Fund)) if f.name == name).id


def test_field_fact_carries_value_and_provenance(db, catalog):
    aid = _fund_id(db, "Alpha Macro Partners")
    fee = catalog.resolve(field_id(aid, "management_fee"))
    assert fee is not None and fee.kind == "field"
    assert fee.value == pytest.approx(0.02)
    assert fee.display == "2.0%"
    assert fee.provenance.startswith("column:")
    assert fee.extra["raw"] == "2%"


def test_metric_fact_has_inputs_provenance(db, catalog):
    aid = _fund_id(db, "Alpha Macro Partners")
    sharpe = catalog.resolve(metric_id(aid, "sharpe"))
    assert sharpe is not None and sharpe.kind == "metric"
    assert sharpe.value is not None
    assert "monthly returns" in sharpe.provenance
    assert "vs SPY" in sharpe.provenance


def test_check_fact_holds_status_and_threshold(db, catalog):
    aid = _fund_id(db, "Alpha Macro Partners")
    chk = catalog.resolve(check_id(aid, "management_fee"))
    assert chk is not None and chk.kind == "check"
    assert chk.value == "fail"  # 2% > 1.8% ceiling
    assert chk.extra["threshold"] == pytest.approx(0.018)
    assert "exceeds" in chk.display


def test_mandate_facts_present(catalog):
    fee = catalog.resolve(mandate_id("max_management_fee"))
    assert fee is not None and fee.value == pytest.approx(0.018)
    excl = catalog.resolve(mandate_id("excluded_strategies"))
    assert excl is not None and "managed_futures" in excl.value


def test_funds_ranked_passed_first(catalog):
    assert catalog.funds[0].rank == 1
    assert catalog.funds[0].passed is True
    # Cobalt is excluded (managed_futures) -> appears last, not passing.
    last = catalog.funds[-1]
    assert last.fund_name == "Cobalt Managed Futures"
    assert last.passed is False


def test_valid_ids_cover_all_emitted_facts(catalog):
    ids = catalog.valid_ids
    # every fact referenced in the per-fund grouping is resolvable
    for ff in catalog.funds:
        for fact in (*ff.fields, *ff.metrics, *ff.checks):
            assert fact.id in ids
            assert catalog.resolve(fact.id) is fact
