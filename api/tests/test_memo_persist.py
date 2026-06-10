"""Memo persistence + serialization (LLM stubbed; refs cite real catalog IDs)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models
from app.db.database import Base
from app.extraction import extract
from app.memo import build_catalog, field_id, metric_id
from app.schemas.fund import Fund
from app.schemas.mandate import MandateSpec
from app.schemas.memo import Claim, MemoDraft, MemoSection
from app.services.evaluation import create_mandate, run_mandate
from app.services.memo import generate_and_persist_memo, serialize_memo
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
def run(db):
    up = save_extraction(
        db, [extract((FIXTURES / "messy_universe.csv").read_bytes(), "u.csv", Fund)]
    )
    ingest_returns_for_upload(
        db, up.id, (FIXTURES / "returns_long.csv").read_bytes(), "r.csv"
    )
    compute_metrics_for_upload(db, up.id)
    mandate = create_mandate(db, MandateSpec(max_management_fee=0.018))
    return run_mandate(db, up.id, mandate)


@pytest.fixture
def memo_out(db, run, monkeypatch):
    # Stub the LLM with a draft that cites real fact IDs from this run's catalog.
    catalog = build_catalog(run)
    alpha = next(f for f in db.scalars(select(models.Fund)) if f.name.startswith("Alpha"))
    fee = field_id(alpha.id, "management_fee")
    sharpe = metric_id(alpha.id, "sharpe")

    draft = MemoDraft(sections=[
        MemoSection(kind="summary", title="Summary", claims=[
            Claim(text="Alpha charges a 2% management fee.", refs=[fee]),
            Claim(text="The team is experienced.", refs=[]),
        ]),
        MemoSection(kind="risks", title="Risks", claims=[
            Claim(text=f"Its Sharpe is {catalog.resolve(sharpe).display}.", refs=[sharpe]),
        ]),
    ]).model_dump()

    from app.extraction.llm import llm
    monkeypatch.setattr(llm, "structured", lambda **k: dict(draft))

    memo = generate_and_persist_memo(db, run)
    return serialize_memo(memo), fee, sharpe


def test_memo_and_claims_persisted(db, memo_out):
    out, _, _ = memo_out
    assert len(list(db.scalars(select(models.Memo)))) == 1
    assert len(list(db.scalars(select(models.MemoSection)))) == 2
    assert len(list(db.scalars(select(models.MemoClaim)))) == 3
    assert out.all_verified is True


def test_sections_and_claims_ordered(memo_out):
    out, _, _ = memo_out
    assert [s.kind for s in out.sections] == ["summary", "risks"]
    assert out.sections[0].claims[0].text.startswith("Alpha charges")


def test_refs_resolved_to_facts(memo_out):
    out, fee, sharpe = memo_out
    assert fee in out.facts and out.facts[fee].display == "2.0%"
    assert sharpe in out.facts and out.facts[sharpe].kind == "metric"


def test_appendix_covers_all_funds(memo_out):
    out, _, _ = memo_out
    assert len(out.appendix) == 5
    assert out.appendix[0].rank == 1


def test_memo_cascade_deletes_with_run(db, run, memo_out):
    db.delete(run)
    db.commit()
    assert db.scalars(select(models.Memo)).first() is None
    assert db.scalars(select(models.MemoClaim)).first() is None
