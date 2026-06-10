"""The mapping-plan schema for the tabular path.

Key idea: the LLM returns a *plan* (which source column feeds which target
field, and what transform to apply) — never the data values themselves. Code
then applies the plan deterministically to every row, so the model is never in
a position to transcribe a number wrong.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Transform(str, Enum):
    NONE = "none"  # pass through (string strip) — value already in target form
    PERCENT_TO_DECIMAL = "percent_to_decimal"  # "2%" or 2.0 -> 0.02
    BPS_TO_DECIMAL = "bps_to_decimal"  # "150 bps" -> 0.015
    STRIP_CURRENCY = "strip_currency"  # "$1,200,000" / "$1.2B" -> 1200000.0
    PARSE_DATE = "parse_date"  # any common date string -> ISO date
    PARSE_INT = "parse_int"  # "12 days" / "12" -> 12
    PARSE_FLOAT = "parse_float"  # "1,234.5" -> 1234.5


class ColumnMap(BaseModel):
    target_field: str = Field(description="Field name in the target schema.")
    source_column: str = Field(description="Exact source column header.")
    transform: Transform = Transform.NONE
    confidence: float | None = Field(
        default=None, ge=0, le=1, description="Mapper confidence, 0-1."
    )
    reasoning: str | None = Field(
        default=None, description="One short clause on why this mapping."
    )


class MappingPlan(BaseModel):
    mappings: list[ColumnMap] = Field(default_factory=list)
    unmapped_columns: list[str] = Field(
        default_factory=list,
        description="Source columns left unmapped (kept for the report).",
    )
