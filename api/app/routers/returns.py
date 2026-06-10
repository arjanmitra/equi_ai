"""Returns endpoints — attach a return series to an existing upload, read it back."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db
from app.schemas.returns import ReturnPointOut, ReturnsIngestResult
from app.services.returns import ingest_returns_for_upload

router = APIRouter(tags=["returns"])


@router.post("/uploads/{upload_id}/returns", response_model=list[ReturnsIngestResult])
async def post_returns(
    upload_id: str, files: list[UploadFile], db: Session = Depends(get_db)
) -> list[ReturnsIngestResult]:
    if db.get(models.Upload, upload_id) is None:
        raise HTTPException(404, "upload not found")
    results: list[ReturnsIngestResult] = []
    for file in files:
        raw = await file.read()
        results.append(
            ingest_returns_for_upload(db, upload_id, raw, file.filename or "returns")
        )
    return results


@router.get("/funds/{fund_id}/returns", response_model=list[ReturnPointOut])
def fund_returns(
    fund_id: str, db: Session = Depends(get_db)
) -> list[models.ReturnObservation]:
    if db.get(models.Fund, fund_id) is None:
        raise HTTPException(404, "fund not found")
    return list(
        db.scalars(
            select(models.ReturnObservation)
            .where(models.ReturnObservation.fund_id == fund_id)
            .order_by(models.ReturnObservation.period)
        )
    )
