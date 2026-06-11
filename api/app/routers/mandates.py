"""Mandate endpoint — create a reusable mandate from the form."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db
from app.schemas.evaluation import MandateOut
from app.schemas.mandate import MandateSpec
from app.services.evaluation import create_mandate

router = APIRouter(tags=["mandates"])


def _to_out(mandate: models.Mandate) -> MandateOut:
    return MandateOut(
        id=mandate.id,
        created_at=mandate.created_at,
        label=mandate.label,
        spec=MandateSpec.model_validate(mandate.spec_json),
    )


@router.post("/mandates", response_model=MandateOut)
def post_mandate(spec: MandateSpec, db: Session = Depends(get_db)) -> MandateOut:
    return _to_out(create_mandate(db, spec))


@router.get("/mandates", response_model=list[MandateOut])
def list_mandates(db: Session = Depends(get_db)) -> list[MandateOut]:
    rows = db.scalars(
        select(models.Mandate).order_by(models.Mandate.created_at.desc())
    ).all()
    return [_to_out(m) for m in rows]


@router.get("/mandates/{mandate_id}", response_model=MandateOut)
def get_mandate(mandate_id: str, db: Session = Depends(get_db)) -> MandateOut:
    mandate = db.get(models.Mandate, mandate_id)
    if mandate is None:
        raise HTTPException(404, "mandate not found")
    return _to_out(mandate)
