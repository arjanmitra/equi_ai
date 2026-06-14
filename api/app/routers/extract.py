"""Extraction endpoints — preview the mapping, then commit + persist.

Two-phase by design:
- `POST /extract/plan` proposes (or re-applies an edited) column→field mapping
  and returns a faithful preview — persisting nothing.
- `POST /extract` commits: it accepts the approved plans, applies them
  deterministically (no LLM), and persists Upload → SourceFile → Fund →
  SourceField in one transaction. Omitting `plans` reproduces the original
  one-shot behavior, so existing callers are unaffected.

`GET /extract/schema` exposes the canonical target fields + transforms so the
review UI's dropdowns stay single-sourced in code.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.extraction import extract
from app.extraction.field_spec import field_specs
from app.schemas.extract_plan import PlanFile, PlanResponse, SchemaResponse, TransformOption
from app.schemas.extraction import ExtractionResult
from app.schemas.fund import Fund
from app.schemas.mapping import MappingPlan, Transform
from app.services.extract_preview import preview_file
from app.services.persistence import save_extraction

router = APIRouter(prefix="/extract", tags=["extraction"])

# Human-friendly labels for the transform dropdown (values mirror the enum).
_TRANSFORM_LABELS: dict[str, str] = {
    "none": "No transform (use as-is)",
    "percent_to_decimal": "Percent → decimal (2% → 0.02)",
    "bps_to_decimal": "Basis points → decimal (150 bps → 0.015)",
    "strip_currency": "Currency → number ($1.2B → 1200000000)",
    "parse_date": "Parse date → ISO",
    "parse_int": "Parse whole number (12 days → 12)",
    "parse_float": "Parse decimal number (1,234.5 → 1234.5)",
}


class ExtractResponse(BaseModel):
    upload_id: str
    results: list[ExtractionResult]


def _parse_plans(plans: str | None) -> dict[str, MappingPlan]:
    """Decode the optional `plans` form field: {filename: MappingPlan}."""
    if not plans:
        return {}
    try:
        raw = json.loads(plans)
        return {name: MappingPlan.model_validate(p) for name, p in raw.items()}
    except (json.JSONDecodeError, ValidationError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid plans: {exc}") from exc


@router.get("/schema", response_model=SchemaResponse)
def get_target_schema() -> SchemaResponse:
    """Canonical Fund fields + available transforms, for the review dropdowns."""
    return SchemaResponse(
        target_fields=field_specs(Fund),
        transforms=[
            TransformOption(value=t.value, label=_TRANSFORM_LABELS.get(t.value, t.value))
            for t in Transform
        ],
    )


@router.post("/plan", response_model=PlanResponse)
async def plan_extraction(
    files: list[UploadFile],
    plans: str | None = Form(default=None),
) -> PlanResponse:
    """Preview the mapping for each file without persisting. Pass `plans` to
    re-apply an edited mapping (live preview on edit) — no LLM call in that case."""
    overrides = _parse_plans(plans)
    out: list[PlanFile] = []
    for file in files:
        raw = await file.read()
        name = file.filename or "upload"
        out.append(preview_file(raw, name, Fund, override=overrides.get(name)))
    return PlanResponse(files=out)


@router.post("", response_model=ExtractResponse)
async def extract_files(
    files: list[UploadFile],
    label: str | None = Form(default=None),
    plans: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> ExtractResponse:
    overrides = _parse_plans(plans)
    results: list[ExtractionResult] = []
    for file in files:
        raw = await file.read()
        name = file.filename or "upload"
        results.append(extract(raw, name, Fund, plan=overrides.get(name)))

    upload = save_extraction(db, results, label=label)
    return ExtractResponse(upload_id=upload.id, results=results)
