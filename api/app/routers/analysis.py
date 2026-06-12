"""Analysis endpoints — the rows in the Analyses table + wizard lifecycle."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db
from app.schemas.analysis import AnalysisCreate, AnalysisOut, AnalysisUpdate
from app.services.analysis import (
    create_analysis,
    delete_analysis,
    serialize_analysis,
    update_analysis,
)

router = APIRouter(tags=["analyses"])


@router.post("/analyses", response_model=AnalysisOut)
def post_analysis(body: AnalysisCreate, db: Session = Depends(get_db)) -> AnalysisOut:
    if db.get(models.Upload, body.upload_id) is None:
        raise HTTPException(404, "upload not found")
    return serialize_analysis(create_analysis(db, body.upload_id, body.label))


@router.get("/analyses", response_model=list[AnalysisOut])
def list_analyses(db: Session = Depends(get_db)) -> list[AnalysisOut]:
    rows = db.scalars(
        select(models.Analysis).order_by(models.Analysis.created_at.desc())
    ).all()
    return [serialize_analysis(a) for a in rows]


@router.get("/analyses/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)) -> AnalysisOut:
    analysis = db.get(models.Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(404, "analysis not found")
    return serialize_analysis(analysis)


@router.patch("/analyses/{analysis_id}", response_model=AnalysisOut)
def patch_analysis(
    analysis_id: str, body: AnalysisUpdate, db: Session = Depends(get_db)
) -> AnalysisOut:
    analysis = db.get(models.Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(404, "analysis not found")
    return serialize_analysis(
        update_analysis(db, analysis, body.model_dump(exclude_unset=True))
    )


@router.delete("/analyses/{analysis_id}", status_code=204)
def remove_analysis(analysis_id: str, db: Session = Depends(get_db)) -> Response:
    analysis = db.get(models.Analysis, analysis_id)
    if analysis is not None:
        delete_analysis(db, analysis)
    return Response(status_code=204)
