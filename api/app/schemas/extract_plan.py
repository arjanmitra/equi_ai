"""DTOs for the mapping-review (plan/preview) step.

`POST /extract/plan` returns, per file, the proposed column→field mapping plus a
faithful preview of the records it would produce — and persists nothing. The UI
edits the plan and either re-previews (same endpoint) or commits it via
`POST /extract`. `GET /extract/schema` feeds the review dropdowns from the
canonical schema so the field list stays single-sourced in code.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.extraction.field_spec import FieldSpec
from app.schemas.extraction import FieldIssue
from app.schemas.mapping import MappingPlan


class PlanFile(BaseModel):
    """Everything the review screen needs for one uploaded file."""

    filename: str
    strategy: str  # "tabular" | "document" | "none"
    plan: MappingPlan | None = Field(
        default=None,
        description="Editable mapping. None when there are no columns to review "
        "(document path) or the file failed to load.",
    )
    columns: list[str] = Field(default_factory=list)
    column_samples: dict[str, list[str]] = Field(default_factory=dict)
    preview: list[dict] = Field(
        default_factory=list, description="First few records the plan would produce."
    )
    structure_notes: list[str] = Field(default_factory=list)
    issues: list[FieldIssue] = Field(default_factory=list)


class PlanResponse(BaseModel):
    files: list[PlanFile]


class TransformOption(BaseModel):
    value: str
    label: str


class SchemaResponse(BaseModel):
    """The canonical target schema + available transforms, for the UI dropdowns."""

    target_fields: list[FieldSpec]
    transforms: list[TransformOption]
