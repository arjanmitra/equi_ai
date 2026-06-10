"""Return-series ingestion: long + wide-by-date shapes, and linking to funds."""

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
from app.returns import ingest_returns
from app.schemas.fund import Fund
from app.services.persistence import save_extraction
from app.services.returns import ingest_returns_for_upload

FIXTURES = Path(__file__).parent / "fixtures"


# --- Pure ingestion (no DB) -------------------------------------------------
def test_long_shape_detected_and_parsed():
    raw = (FIXTURES / "returns_long.csv").read_bytes()
    ext = ingest_returns(raw, "returns_long.csv")
    assert ext.shape == "long"
    assert len(ext.records) == 6
    alpha_jan = next(
        r for r in ext.records
        if r.fund_ref == "Alpha Macro Partners" and r.period == date(2023, 1, 1)
    )
    assert alpha_jan.value == pytest.approx(0.012)  # "1.2%" -> 0.012
    neg = next(r for r in ext.records if r.period == date(2023, 2, 1) and r.fund_ref.startswith("Alpha"))
    assert neg.value == pytest.approx(-0.008)


def test_wide_shape_melted():
    raw = (FIXTURES / "returns_wide.csv").read_bytes()
    ext = ingest_returns(raw, "returns_wide.csv")
    assert ext.shape == "wide"
    assert len(ext.records) == 6  # 2 funds x 3 months
    cobalt_mar = next(
        r for r in ext.records
        if r.fund_ref == "Cobalt Managed Futures" and r.period == date(2023, 3, 1)
    )
    assert cobalt_mar.value == pytest.approx(-0.010)
    # periods normalized to first of month from "Jan-23" style headers
    assert {r.period for r in ext.records} == {
        date(2023, 1, 1), date(2023, 2, 1), date(2023, 3, 1)
    }


# --- Linking into the DB ----------------------------------------------------
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
    return save_extraction(db, [extract(raw, "messy_universe.csv", Fund)])


def test_long_returns_linked_to_funds(db, upload):
    raw = (FIXTURES / "returns_long.csv").read_bytes()
    result = ingest_returns_for_upload(db, upload.id, raw, "returns_long.csv")

    assert result.shape == "long"
    assert result.observations_written == 5  # Alpha(3) + Beacon(2); Zeta unmatched
    assert set(result.matched_funds) == {"Alpha Macro Partners", "Beacon L/S Equity"}
    assert result.unmatched_refs == ["Zeta Opportunities"]
    assert result.period_start == date(2023, 1, 1)
    assert result.period_end == date(2023, 3, 1)


def test_observations_attached_to_correct_fund(db, upload):
    raw = (FIXTURES / "returns_long.csv").read_bytes()
    ingest_returns_for_upload(db, upload.id, raw, "returns_long.csv")

    alpha = next(
        f for f in db.scalars(select(models.Fund)) if f.name == "Alpha Macro Partners"
    )
    obs = sorted(alpha.returns, key=lambda o: o.period)
    assert [o.period for o in obs] == [date(2023, 1, 1), date(2023, 2, 1), date(2023, 3, 1)]
    assert obs[0].value == pytest.approx(0.012)


def test_wide_returns_linked(db, upload):
    raw = (FIXTURES / "returns_wide.csv").read_bytes()
    result = ingest_returns_for_upload(db, upload.id, raw, "returns_wide.csv")
    assert result.shape == "wide"
    assert result.observations_written == 6
    assert set(result.matched_funds) == {"Alpha Macro Partners", "Cobalt Managed Futures"}


def test_ingestion_is_idempotent(db, upload):
    raw = (FIXTURES / "returns_long.csv").read_bytes()
    ingest_returns_for_upload(db, upload.id, raw, "returns_long.csv")
    ingest_returns_for_upload(db, upload.id, raw, "returns_long.csv")  # again
    # Still 5 observations, not 10 — upsert per (fund, period).
    assert len(list(db.scalars(select(models.ReturnObservation)))) == 5


def test_returns_cascade_delete_with_upload(db, upload):
    raw = (FIXTURES / "returns_long.csv").read_bytes()
    ingest_returns_for_upload(db, upload.id, raw, "returns_long.csv")
    assert db.scalars(select(models.ReturnObservation)).first() is not None
    db.delete(upload)
    db.commit()
    assert db.scalars(select(models.ReturnObservation)).first() is None
