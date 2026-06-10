"""Round-trip: extract a messy CSV, persist it, read it back from SQLite.

Verifies the relational audit model holds — funds as typed columns, provenance
linked to the right fund, and cascade delete cleaning up children.
"""

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
from app.services.persistence import save_extraction

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def db():
    # In-memory SQLite, single shared connection (StaticPool) so the schema
    # persists across the session within one test.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def upload(db):
    raw = (FIXTURES / "messy_universe.csv").read_bytes()
    result = extract(raw, "messy_universe.csv", Fund)
    return save_extraction(db, [result], label="test")


def test_upload_and_source_file_persisted(db, upload):
    assert upload.id and upload.label == "test"
    files = list(db.scalars(select(models.SourceFile)))
    assert len(files) == 1
    assert files[0].extraction_path == "tabular"
    assert files[0].records_ok == 5
    assert files[0].records_failed == 0
    assert files[0].mime == "text/csv"


def test_funds_persisted_as_typed_columns(db, upload):
    funds = list(db.scalars(select(models.Fund)))
    assert len(funds) == 5
    alpha = next(f for f in funds if f.name == "Alpha Macro Partners")
    assert alpha.management_fee == pytest.approx(0.02)
    assert alpha.aum_usd == pytest.approx(1_200_000_000.0)
    assert alpha.strategy == "global_macro"
    assert alpha.business_key == "alpha-macro-partners"
    assert alpha.inception_date.isoformat() == "2018-01-01"


def test_provenance_linked_to_correct_fund(db, upload):
    alpha = next(
        f for f in db.scalars(select(models.Fund)) if f.name == "Alpha Macro Partners"
    )
    fee_prov = next(
        sf for sf in alpha.source_fields if sf.target_field == "management_fee"
    )
    assert fee_prov.raw_value == "2%"
    assert fee_prov.normalized_value == pytest.approx(0.02)
    assert fee_prov.source.startswith("column:")
    # Every source field belongs to this fund.
    assert all(sf.fund_id == alpha.id for sf in alpha.source_fields)


def test_provenance_count_matches_extraction(db, upload):
    # 5 funds, each with provenance for every mapped column.
    total = len(list(db.scalars(select(models.SourceField))))
    assert total > 0
    funds = list(db.scalars(select(models.Fund)))
    assert total == sum(len(f.source_fields) for f in funds)


def test_cascade_delete_removes_children(db, upload):
    db.delete(upload)
    db.commit()
    assert db.scalars(select(models.Fund)).first() is None
    assert db.scalars(select(models.SourceField)).first() is None
    assert db.scalars(select(models.SourceFile)).first() is None
