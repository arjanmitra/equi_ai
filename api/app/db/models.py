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

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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
    runs: Mapped[list[MandateRun]] = relationship(
        back_populates="upload", cascade="all, delete-orphan"
    )


class SourceFile(Base):
    """One uploaded file within an Upload, plus its extraction outcome."""

    __tablename__ = "source_files"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id"))
    filename: Mapped[str] = mapped_column(String)
    mime: Mapped[str | None] = mapped_column(String, nullable=True)
    kind: Mapped[str] = mapped_column(String, default="universe")  # universe | returns
    extraction_path: Mapped[str] = mapped_column(String)  # tabular / document / none / long / wide
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
    returns: Mapped[list[ReturnObservation]] = relationship(
        back_populates="fund", cascade="all, delete-orphan"
    )
    metrics: Mapped[FundMetrics | None] = relationship(
        back_populates="fund", uselist=False, cascade="all, delete-orphan"
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
    # "field" = mapped canonical value (trusted); "extra" = unmapped reported
    # attribute (never feeds metrics/constraints). See FieldProvenance.kind.
    kind: Mapped[str] = mapped_column(String, default="field")

    fund: Mapped[Fund] = relationship(back_populates="source_fields")


class ReturnObservation(Base):
    """One monthly return for one fund (decimal). The metrics stage reads these."""

    __tablename__ = "return_observations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    fund_id: Mapped[str] = mapped_column(ForeignKey("funds.id"))
    period: Mapped[date] = mapped_column(Date)  # first of the month
    value: Mapped[float] = mapped_column(Float)  # decimal monthly return

    fund: Mapped[Fund] = relationship(back_populates="returns")


class FundMetrics(Base):
    """Computed risk/return metrics for one fund (upload-scoped, 1:1 with Fund).

    inputs_json records what the numbers were computed from (n obs, date range,
    benchmark, risk-free source, rf rate used) so the memo can cite each metric's
    basis — the audit hook for metrics, mirroring SourceField for raw data."""

    __tablename__ = "fund_metrics"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    fund_id: Mapped[str] = mapped_column(ForeignKey("funds.id"), unique=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    benchmark_ticker: Mapped[str | None] = mapped_column(String, nullable=True)
    n_obs: Mapped[int] = mapped_column(Integer, default=0)
    annualized_volatility: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(Float, nullable=True)
    annualized_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    cumulative_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    correlation_benchmark: Mapped[float | None] = mapped_column(Float, nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    inputs_json: Mapped[dict] = mapped_column(JSON, default=dict)

    fund: Mapped[Fund] = relationship(back_populates="metrics")


class BenchmarkSeries(Base):
    """Cached monthly market data, keyed by ticker. For an index ticker the
    value is a monthly return; for the risk-free ticker (DGS3MO) it is the
    annualized rate as a decimal. Cached so we don't refetch external APIs."""

    __tablename__ = "benchmark_series"
    __table_args__ = (UniqueConstraint("ticker", "period", name="uq_ticker_period"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    ticker: Mapped[str] = mapped_column(String, index=True)
    period: Mapped[date] = mapped_column(Date)  # first of the month
    value: Mapped[float] = mapped_column(Float)


class Mandate(Base):
    """A reusable set of allocator constraints (the MandateSpec, as JSON)."""

    __tablename__ = "mandates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    label: Mapped[str | None] = mapped_column(String, nullable=True)
    spec_json: Mapped[dict] = mapped_column(JSON, default=dict)

    runs: Mapped[list[MandateRun]] = relationship(back_populates="mandate")


class MandateRun(Base):
    """Evaluating one mandate against one upload's funds. The anchor that the
    metrics + memo stages will attach to."""

    __tablename__ = "mandate_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id"))
    mandate_id: Mapped[str] = mapped_column(ForeignKey("mandates.id"))

    upload: Mapped[Upload] = relationship(back_populates="runs")
    mandate: Mapped[Mandate] = relationship(back_populates="runs")
    evaluations: Mapped[list[FundEvaluation]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    memos: Mapped[list[Memo]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class FundEvaluation(Base):
    """One fund's verdict under one run: pass/fail, score, per-constraint checks."""

    __tablename__ = "fund_evaluations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    mandate_run_id: Mapped[str] = mapped_column(ForeignKey("mandate_runs.id"))
    fund_id: Mapped[str] = mapped_column(ForeignKey("funds.id"))
    passed: Mapped[bool] = mapped_column(Boolean)
    score: Mapped[float] = mapped_column(Float)
    checks_json: Mapped[list] = mapped_column(JSON, default=list)

    run: Mapped[MandateRun] = relationship(back_populates="evaluations")
    fund: Mapped[Fund] = relationship()


class Memo(Base):
    """A generated, verified IC memo for one mandate run."""

    __tablename__ = "memos"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    mandate_run_id: Mapped[str] = mapped_column(ForeignKey("mandate_runs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    model: Mapped[str] = mapped_column(String)
    all_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    log_json: Mapped[list] = mapped_column(JSON, default=list)

    run: Mapped[MandateRun] = relationship(back_populates="memos")
    sections: Mapped[list[MemoSection]] = relationship(
        back_populates="memo", cascade="all, delete-orphan"
    )


class MemoSection(Base):
    __tablename__ = "memo_sections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    memo_id: Mapped[str] = mapped_column(ForeignKey("memos.id"))
    kind: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    position: Mapped[int] = mapped_column(Integer, default=0)

    memo: Mapped[Memo] = relationship(back_populates="sections")
    claims: Mapped[list[MemoClaim]] = relationship(
        back_populates="section", cascade="all, delete-orphan"
    )


class Analysis(Base):
    """One end-to-end analysis: an upload (universe + returns) → mandate → run →
    memo. The lifecycle pointers fill in as the New Analysis wizard progresses;
    this is the row in the Analyses table."""

    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    label: Mapped[str | None] = mapped_column(String, nullable=True)
    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id"))
    mandate_id: Mapped[str | None] = mapped_column(ForeignKey("mandates.id"), nullable=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("mandate_runs.id"), nullable=True)
    memo_id: Mapped[str | None] = mapped_column(ForeignKey("memos.id"), nullable=True)

    upload: Mapped[Upload] = relationship()


class MemoClaim(Base):
    """One claim: prose + the fact IDs it cites + its verification verdict."""

    __tablename__ = "memo_claims"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    section_id: Mapped[str] = mapped_column(ForeignKey("memo_sections.id"))
    position: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    refs_json: Mapped[list] = mapped_column(JSON, default=list)
    verified: Mapped[bool] = mapped_column(Boolean, default=True)
    issues_json: Mapped[list] = mapped_column(JSON, default=list)

    section: Mapped[MemoSection] = relationship(back_populates="claims")
