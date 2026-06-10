"""Outputs of the extraction layer.

The shape here is what makes the layer reusable: every record ships with
provenance (where each value came from) and a validation report (what was
cleaned). Provenance is captured at extraction time precisely so the downstream
audit trail does not have to reverse-engineer it.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IssueLevel(str, Enum):
    INFO = "info"  # something was inferred/coerced but is fine
    FLAG = "flag"  # usable but suspicious (e.g. implausible value) -> soft flag
    ERROR = "error"  # could not coerce -> hard failure, record dropped


class FieldIssue(BaseModel):
    level: IssueLevel
    message: str
    record_index: int | None = Field(
        default=None, description="Row/record this issue belongs to, if any."
    )
    field: str | None = Field(
        default=None, description="Target field this issue belongs to, if any."
    )


class FieldProvenance(BaseModel):
    """Links one normalized value back to its origin. Powers the audit trail."""

    record_index: int
    target_field: str
    raw_value: Any = Field(description="The original value before any transform.")
    normalized_value: Any = Field(description="The value after transform/coercion.")
    source: str = Field(
        description="Human-readable origin, e.g. 'column: Net Ret %' or "
        "'page 2, snippet ...'."
    )
    transform: str | None = Field(
        default=None, description="Transform applied, if any."
    )
    confidence: float | None = None


class ValidationReport(BaseModel):
    total_rows: int = 0
    records_ok: int = 0
    records_failed: int = 0
    unmapped_columns: list[str] = Field(default_factory=list)
    issues: list[FieldIssue] = Field(default_factory=list)

    def add(
        self,
        level: IssueLevel,
        message: str,
        *,
        record_index: int | None = None,
        field: str | None = None,
    ) -> None:
        self.issues.append(
            FieldIssue(
                level=level, message=message, record_index=record_index, field=field
            )
        )


class ExtractionResult(BaseModel):
    source_name: str
    target_schema: str
    strategy: str = Field(
        description="Which mapping path ran: 'tabular' or 'document'."
    )
    records: list[dict] = Field(
        default_factory=list,
        description="Validated records, serialized (model_dump).",
    )
    provenance: list[FieldProvenance] = Field(default_factory=list)
    report: ValidationReport = Field(default_factory=ValidationReport)
