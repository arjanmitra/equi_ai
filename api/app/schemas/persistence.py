"""API read-models for the persisted audit data (ORM -> JSON)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SourceFieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    target_field: str
    raw_value: str | None
    normalized_value: Any | None
    source: str
    transform: str | None
    confidence: float | None


class FundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    upload_id: str
    source_file_id: str
    business_key: str
    name: str
    strategy: str | None
    redemption_frequency: str | None
    notice_period_days: int | None
    lockup_months: int | None
    management_fee: float | None
    performance_fee: float | None
    aum_usd: float | None
    inception_date: date | None
    notes: str | None


class SourceFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    mime: str | None
    kind: str
    extraction_path: str
    records_ok: int
    records_failed: int
    report_json: dict | None = None


class UploadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    label: str | None
    source_files: list[SourceFileOut]
