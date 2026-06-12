"""Analysis lifecycle + returns-file persistence."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models
from app.db.database import Base
from app.extraction import extract
from app.schemas.fund import Fund
from app.services.analysis import (
    create_analysis,
    delete_analysis,
    serialize_analysis,
    update_analysis,
)
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
def upload(db):
    raw = (FIXTURES / "messy_universe.csv").read_bytes()
    return save_extraction(db, [extract(raw, "messy_universe.csv", Fund)])


def test_create_defaults_label_to_universe_file(db, upload):
    out = serialize_analysis(create_analysis(db, upload.id))
    assert out.label == "messy_universe.csv"
    assert out.universe_files == ["messy_universe.csv"]
    assert out.returns_files == []
    assert out.has_memo is False


def test_returns_file_is_recorded(db, upload):
    a = create_analysis(db, upload.id)
    ingest_returns_for_upload(
        db, upload.id, (FIXTURES / "returns_long.csv").read_bytes(), "returns_long.csv"
    )
    db.refresh(a)
    assert "returns_long.csv" in serialize_analysis(a).returns_files
    # universe file is unchanged / not double-counted
    assert serialize_analysis(a).universe_files == ["messy_universe.csv"]


def test_update_sets_lifecycle_pointers(db, upload):
    a = create_analysis(db, upload.id)
    update_analysis(db, a, {"label": "Q1 review"})
    assert serialize_analysis(a).label == "Q1 review"


def test_delete_cascades_the_upload(db, upload):
    a = create_analysis(db, upload.id)
    delete_analysis(db, a)
    assert db.get(models.Analysis, a.id) is None
    assert db.get(models.Upload, upload.id) is None
    assert db.scalars(select(models.Fund)).first() is None
