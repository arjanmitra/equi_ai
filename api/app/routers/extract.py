"""Extraction endpoint — ingests files, persists, and returns the results.

Upload one or more files; each is run through the engine toward the canonical
Fund schema, then the whole batch is persisted (Upload -> SourceFile -> Fund ->
SourceField) in one transaction. Returns the new `upload_id` plus the per-file
records, provenance, and validation report so the frontend can show what was
cleaned. Later pipeline stages (mandate runs, metrics, memo) build on the
persisted Upload.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.extraction import extract
from app.schemas.extraction import ExtractionResult
from app.schemas.fund import Fund
from app.services.persistence import save_extraction

router = APIRouter(prefix="/extract", tags=["extraction"])


class ExtractResponse(BaseModel):
    upload_id: str
    results: list[ExtractionResult]


@router.post("", response_model=ExtractResponse)
async def extract_files(
    files: list[UploadFile],
    label: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> ExtractResponse:
    results: list[ExtractionResult] = []
    for file in files:
        raw = await file.read()
        results.append(extract(raw, file.filename or "upload", Fund))

    upload = save_extraction(db, results, label=label)
    return ExtractResponse(upload_id=upload.id, results=results)
