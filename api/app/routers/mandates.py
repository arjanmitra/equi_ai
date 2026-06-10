"""Mandate endpoint — create a reusable mandate from the form."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.evaluation import MandateOut
from app.schemas.mandate import MandateSpec
from app.services.evaluation import create_mandate

router = APIRouter(tags=["mandates"])


@router.post("/mandates", response_model=MandateOut)
def post_mandate(spec: MandateSpec, db: Session = Depends(get_db)) -> MandateOut:
    mandate = create_mandate(db, spec)
    return MandateOut(
        id=mandate.id,
        created_at=mandate.created_at,
        label=mandate.label,
        spec=MandateSpec.model_validate(mandate.spec_json),
    )
