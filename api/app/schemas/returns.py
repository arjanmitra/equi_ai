"""Schemas for return-series ingestion.

A return series is a 1:N time series per fund, so it can't live on the scalar
Fund schema — it becomes ReturnObservation rows. Ingestion produces canonical
`(fund_ref, period, value)` triples (value = decimal monthly return), which a
service then links to persisted funds by name.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.schemas.extraction import ValidationReport


class ReturnRecord(BaseModel):
    fund_ref: str  # the fund name/id as written in the source (pre-linking)
    period: date  # normalized to the first of the month
    value: float  # decimal monthly return (0.012 = +1.2%)


class ReturnsExtraction(BaseModel):
    source_name: str
    shape: str  # "long" | "wide" | "none"
    records: list[ReturnRecord]
    report: ValidationReport


class ReturnsIngestResult(BaseModel):
    """Endpoint response: what was written and how linking went."""

    upload_id: str
    source_name: str
    shape: str
    observations_written: int
    matched_funds: list[str]
    unmatched_refs: list[str]  # series whose fund_ref matched no fund in the upload
    period_start: date | None
    period_end: date | None
    report: ValidationReport


class ReturnPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period: date
    value: float
