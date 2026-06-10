"""Run endpoints — evaluate a mandate against an upload, fetch ranked results.

The run body accepts either an existing `mandate_id` (reuse) or an inline
`mandate` spec (convenience, persisted on the fly).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db
from app.schemas.evaluation import RunOut
from app.schemas.mandate import MandateSpec
from app.services.evaluation import create_mandate, run_mandate, serialize_run

router = APIRouter(tags=["runs"])


class RunRequest(BaseModel):
    mandate_id: str | None = None
    mandate: MandateSpec | None = None

    @model_validator(mode="after")
    def _one_of(self) -> "RunRequest":
        if not self.mandate_id and self.mandate is None:
            raise ValueError("provide either mandate_id or an inline mandate")
        return self


@router.post("/uploads/{upload_id}/runs", response_model=RunOut)
def post_run(
    upload_id: str, body: RunRequest, db: Session = Depends(get_db)
) -> RunOut:
    if db.get(models.Upload, upload_id) is None:
        raise HTTPException(404, "upload not found")

    if body.mandate_id:
        mandate = db.get(models.Mandate, body.mandate_id)
        if mandate is None:
            raise HTTPException(404, "mandate not found")
    else:
        mandate = create_mandate(db, body.mandate)

    run = run_mandate(db, upload_id, mandate)
    return serialize_run(run)


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: str, db: Session = Depends(get_db)) -> RunOut:
    run = db.get(models.MandateRun, run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    return serialize_run(run)
