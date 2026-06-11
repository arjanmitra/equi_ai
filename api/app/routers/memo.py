"""Memo endpoints — generate for a run, fetch with resolved citations."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db
from app.extraction.llm import llm
from app.schemas.memo import MemoOut
from app.services.export import memo_to_docx, memo_to_pdf
from app.services.memo import generate_and_persist_memo, serialize_memo


class MemoSummary(BaseModel):
    id: str
    run_id: str
    created_at: datetime
    model: str
    all_verified: bool
    label: str | None  # the mandate's label, for display

_EXPORTS = {
    "pdf": ("application/pdf", memo_to_pdf),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        memo_to_docx,
    ),
}

router = APIRouter(tags=["memo"])


@router.get("/memos", response_model=list[MemoSummary])
def list_memos(db: Session = Depends(get_db)) -> list[MemoSummary]:
    rows = db.scalars(
        select(models.Memo).order_by(models.Memo.created_at.desc())
    ).all()
    return [
        MemoSummary(
            id=m.id,
            run_id=m.mandate_run_id,
            created_at=m.created_at,
            model=m.model,
            all_verified=m.all_verified,
            label=m.run.mandate.label if m.run and m.run.mandate else None,
        )
        for m in rows
    ]


@router.post("/runs/{run_id}/memo", response_model=MemoOut)
def create_memo(run_id: str, db: Session = Depends(get_db)) -> MemoOut:
    run = db.get(models.MandateRun, run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    if not llm.available:
        raise HTTPException(400, "memo generation requires ANTHROPIC_API_KEY")
    memo = generate_and_persist_memo(db, run)
    return serialize_memo(memo)


@router.get("/memos/{memo_id}", response_model=MemoOut)
def get_memo(memo_id: str, db: Session = Depends(get_db)) -> MemoOut:
    memo = db.get(models.Memo, memo_id)
    if memo is None:
        raise HTTPException(404, "memo not found")
    return serialize_memo(memo)


@router.get("/memos/{memo_id}/export")
def export_memo(
    memo_id: str, format: str = "pdf", db: Session = Depends(get_db)
) -> Response:
    if format not in _EXPORTS:
        raise HTTPException(400, "format must be 'pdf' or 'docx'")
    memo = db.get(models.Memo, memo_id)
    if memo is None:
        raise HTTPException(404, "memo not found")
    media_type, renderer = _EXPORTS[format]
    content = renderer(serialize_memo(memo))
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="ic-memo.{format}"'},
    )


@router.get("/runs/{run_id}/memo", response_model=MemoOut)
def get_run_memo(run_id: str, db: Session = Depends(get_db)) -> MemoOut:
    """The most recent memo for a run."""
    if db.get(models.MandateRun, run_id) is None:
        raise HTTPException(404, "run not found")
    memo = db.scalars(
        select(models.Memo)
        .where(models.Memo.mandate_run_id == run_id)
        .order_by(models.Memo.created_at.desc())
    ).first()
    if memo is None:
        raise HTTPException(404, "no memo for this run yet")
    return serialize_memo(memo)
