"""The relational audit model (ingestion side).

    Upload ─1:N─> SourceFile ─1:N─> Fund ─1:N─> SourceField

`Fund` mirrors the canonical Pydantic schema as typed columns so funds are
queryable/filterable in SQL. `SourceField` is the provenance backbone: one row
per extracted value, holding both the raw and normalized forms plus where it
came from — this is what makes every persisted value traceable, and what the
later memo's audit trail links its claims back to.

Note the name `Fund` here is the ORM entity; the Pydantic `Fund` lives in
app.schemas.fund. They sit in different layers and are never imported together.
Mandate / MandateRun / FundEvaluation arrive in the next step.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Upload(Base):
    """One ingestion batch (the files submitted in a single /extract call)."""

    __tablename__ = "uploads"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    label: Mapped[str | None] = mapped_column(String, nullable=True)

    source_files: Mapped[list[SourceFile]] = relationship(
        back_populates="upload", cascade="all, delete-orphan"
    )
    funds: Mapped[list[Fund]] = relationship(
        back_populates="upload", cascade="all, delete-orphan"
    )


class SourceFile(Base):
    """One uploaded file within an Upload, plus its extraction outcome."""

    __tablename__ = "source_files"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id"))
    filename: Mapped[str] = mapped_column(String)
    mime: Mapped[str | None] = mapped_column(String, nullable=True)
    extraction_path: Mapped[str] = mapped_column(String)  # tabular / document / none
    records_ok: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    report_json: Mapped[dict] = mapped_column(JSON, default=dict)

    upload: Mapped[Upload] = relationship(back_populates="source_files")
    funds: Mapped[list[Fund]] = relationship(
        back_populates="source_file", cascade="all, delete-orphan"
    )


class Fund(Base):
    """A canonical fund row (the Pydantic Fund schema, persisted as columns)."""

    __tablename__ = "funds"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id"))
    source_file_id: Mapped[str] = mapped_column(ForeignKey("source_files.id"))

    business_key: Mapped[str] = mapped_column(String)  # the slug fund_id
    name: Mapped[str] = mapped_column(String)
    strategy: Mapped[str | None] = mapped_column(String, nullable=True)
    redemption_frequency: Mapped[str | None] = mapped_column(String, nullable=True)
    notice_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lockup_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    management_fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    performance_fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    aum_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    inception_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    upload: Mapped[Upload] = relationship(back_populates="funds")
    source_file: Mapped[SourceFile] = relationship(back_populates="funds")
    source_fields: Mapped[list[SourceField]] = relationship(
        back_populates="fund", cascade="all, delete-orphan"
    )


class SourceField(Base):
    """Provenance: one extracted value, traced back to its origin."""

    __tablename__ = "source_fields"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    fund_id: Mapped[str] = mapped_column(ForeignKey("funds.id"))
    target_field: Mapped[str] = mapped_column(String)
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    # normalized_value can be str/int/float/None — stored as JSON to keep type.
    normalized_value: Mapped[object | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String)  # e.g. "column: Mgmt Fee"
    transform: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    fund: Mapped[Fund] = relationship(back_populates="source_fields")
