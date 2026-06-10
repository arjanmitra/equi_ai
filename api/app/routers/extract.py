"""Extraction endpoint — the first vertical slice of the pipeline.

Upload one or more files; each is run through the engine toward the canonical
Fund schema. Returns the records, provenance, and validation report so the
frontend can show what was cleaned. Later pipeline stages (benchmarks, metrics,
memo) build on these records.
"""

from __future__ import annotations

from fastapi import APIRouter, UploadFile

from app.extraction import extract
from app.schemas.extraction import ExtractionResult
from app.schemas.fund import Fund

router = APIRouter(prefix="/extract", tags=["extraction"])


@router.post("", response_model=list[ExtractionResult])
async def extract_files(files: list[UploadFile]) -> list[ExtractionResult]:
    results: list[ExtractionResult] = []
    for file in files:
        raw = await file.read()
        results.append(extract(raw, file.filename or "upload", Fund))
    return results
