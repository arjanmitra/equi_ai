"""Metrics endpoints — compute per-fund metrics for an upload, read them back."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db
from app.schemas.metrics import FundMetricsOut
from app.services.metrics import compute_metrics_for_upload, serialize_metrics

router = APIRouter(tags=["metrics"])


class MetricsRequest(BaseModel):
    # strategy -> ticker overrides for the benchmark mapping
    overrides: dict[str, str] = Field(default_factory=dict)


@router.post("/uploads/{upload_id}/metrics", response_model=list[FundMetricsOut])
def compute_metrics(
    upload_id: str,
    body: MetricsRequest = MetricsRequest(),
    db: Session = Depends(get_db),
) -> list[FundMetricsOut]:
    if db.get(models.Upload, upload_id) is None:
        raise HTTPException(404, "upload not found")
    fms = compute_metrics_for_upload(db, upload_id, body.overrides)
    return [serialize_metrics(fm) for fm in fms]


@router.get("/uploads/{upload_id}/metrics", response_model=list[FundMetricsOut])
def get_metrics(
    upload_id: str, db: Session = Depends(get_db)
) -> list[FundMetricsOut]:
    if db.get(models.Upload, upload_id) is None:
        raise HTTPException(404, "upload not found")
    fms = db.scalars(
        select(models.FundMetrics)
        .join(models.Fund)
        .where(models.Fund.upload_id == upload_id)
    ).all()
    return [serialize_metrics(fm) for fm in fms]
