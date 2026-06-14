"""Mapping-review (plan/preview) step.

Two levels: the `preview_file` service (plan inference, override application,
document-path handling) and the HTTP endpoints (no-persistence guarantee on
`/extract/plan`, `plans` parsing on commit, and the schema endpoint).

All run offline (conftest forces the heuristic), so the inferred plans are
deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models
from app.db.database import Base, get_db
from app.main import app
from app.schemas.fund import Fund
from app.schemas.mapping import ColumnMap, MappingPlan, Transform
from app.services.extract_preview import preview_file

FIXTURES = Path(__file__).parent / "fixtures"


def _bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# --- service: preview_file -------------------------------------------------

def test_preview_returns_editable_plan_and_faithful_preview():
    pf = preview_file(_bytes("messy_universe.csv"), "messy_universe.csv", Fund)
    assert pf.strategy == "tabular"
    assert pf.plan is not None and pf.plan.mappings
    assert "Fund Name" in pf.columns
    assert pf.column_samples  # samples for the UI
    # Preview is the real apply path: a name maps through.
    names = {r.get("name") for r in pf.preview}
    assert "Alpha Macro Partners" in names


def test_override_is_honored_in_preview():
    """Live-preview-on-edit: re-pointing a column changes the produced record."""
    override = MappingPlan(
        mappings=[
            ColumnMap(source_column="Fund Name", target_field="name", transform=Transform.NONE),
            # deliberately send the fee column to performance_fee, not management_fee
            ColumnMap(
                source_column="Mgmt Fee",
                target_field="performance_fee",
                transform=Transform.PERCENT_TO_DECIMAL,
            ),
        ]
    )
    pf = preview_file(
        _bytes("extra_columns_universe.csv"),
        "extra_columns_universe.csv",
        Fund,
        override=override,
    )
    alpha = next(r for r in pf.preview if r["name"] == "Alpha Macro Partners")
    assert alpha["performance_fee"] == pytest.approx(0.02)  # 2% -> 0.02, per override
    assert alpha["management_fee"] is None  # not mapped anymore


def test_document_path_has_no_plan_to_review():
    # An HTML/PDF would hit the document path; here a non-tabular byte blob that
    # the router can't load tabularly still degrades to a reviewable-less result.
    pf = preview_file(b"%PDF-1.4 not really", "mystery.pdf", Fund)
    assert pf.plan is None
    assert pf.strategy in {"document", "none"}


# --- HTTP endpoints --------------------------------------------------------

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
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_plan_endpoint_persists_nothing(client, db):
    resp = client.post(
        "/extract/plan",
        files={"files": ("messy_universe.csv", _bytes("messy_universe.csv"), "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["files"][0]["strategy"] == "tabular"
    assert body["files"][0]["plan"]["mappings"]
    # The whole point: preview writes nothing.
    assert db.scalar(select(func.count(models.Upload.id))) == 0


def test_commit_applies_supplied_plan(client, db):
    override = {
        "extra_columns_universe.csv": MappingPlan(
            mappings=[
                ColumnMap(source_column="Fund Name", target_field="name"),
                ColumnMap(
                    source_column="Mgmt Fee",
                    target_field="performance_fee",
                    transform=Transform.PERCENT_TO_DECIMAL,
                ),
            ]
        ).model_dump(mode="json")
    }
    resp = client.post(
        "/extract",
        files={
            "files": (
                "extra_columns_universe.csv",
                _bytes("extra_columns_universe.csv"),
                "text/csv",
            )
        },
        data={"plans": json.dumps(override)},
    )
    assert resp.status_code == 200
    upload_id = resp.json()["upload_id"]
    funds = db.scalars(
        select(models.Fund).where(models.Fund.upload_id == upload_id)
    ).all()
    alpha = next(f for f in funds if f.name == "Alpha Macro Partners")
    assert alpha.performance_fee == pytest.approx(0.02)
    assert alpha.management_fee is None  # the override didn't map it


def test_commit_without_plans_is_unchanged(client, db):
    resp = client.post(
        "/extract",
        files={"files": ("messy_universe.csv", _bytes("messy_universe.csv"), "text/csv")},
    )
    assert resp.status_code == 200
    upload_id = resp.json()["upload_id"]
    count = db.scalar(
        select(func.count(models.Fund.id)).where(models.Fund.upload_id == upload_id)
    )
    assert count == 5  # same as the original one-shot extract


def test_schema_endpoint_feeds_dropdowns(client):
    body = client.get("/extract/schema").json()
    names = {f["name"] for f in body["target_fields"]}
    assert {"name", "management_fee", "aum_usd"} <= names
    transform_values = {t["value"] for t in body["transforms"]}
    assert "percent_to_decimal" in transform_values
