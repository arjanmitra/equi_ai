"""Read endpoints over the persisted audit data.

These back the funds grid and the audit view: list an upload's funds, and pull
the provenance (source fields) for any one fund.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db
from app.schemas.persistence import FundOut, SourceFieldOut, UploadOut

router = APIRouter(tags=["data"])


@router.get("/uploads/{upload_id}", response_model=UploadOut)
def get_upload(upload_id: str, db: Session = Depends(get_db)) -> models.Upload:
    upload = db.get(models.Upload, upload_id)
    if upload is None:
        raise HTTPException(404, "upload not found")
    return upload


@router.get("/uploads/{upload_id}/funds", response_model=list[FundOut])
def list_funds(upload_id: str, db: Session = Depends(get_db)) -> list[models.Fund]:
    if db.get(models.Upload, upload_id) is None:
        raise HTTPException(404, "upload not found")
    return list(
        db.scalars(
            select(models.Fund).where(models.Fund.upload_id == upload_id)
        )
    )


@router.get("/funds/{fund_id}/provenance", response_model=list[SourceFieldOut])
def fund_provenance(
    fund_id: str, db: Session = Depends(get_db)
) -> list[models.SourceField]:
    if db.get(models.Fund, fund_id) is None:
        raise HTTPException(404, "fund not found")
    return list(
        db.scalars(
            select(models.SourceField).where(models.SourceField.fund_id == fund_id)
        )
    )
