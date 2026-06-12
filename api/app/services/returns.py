"""Ingest a returns file for an upload and link each series to a persisted Fund.

Linking is by normalized fund name within the upload (the entity-resolution cut
we agreed on). Series whose name matches no fund are reported, not fatal.
Observations are de-duplicated per (fund, period) within a single call.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.returns import ingest_returns
from app.schemas.returns import ReturnsIngestResult


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def ingest_returns_for_upload(
    db: Session, upload_id: str, raw: bytes, filename: str
) -> ReturnsIngestResult:
    extraction = ingest_returns(raw, filename)

    funds = db.scalars(
        select(models.Fund).where(models.Fund.upload_id == upload_id)
    ).all()
    by_name = {_norm(f.name): f for f in funds}

    matched: dict[str, str] = {}  # fund_id -> name
    unmatched: set[str] = set()
    deduped: dict[tuple[str, object], float] = {}  # (fund_id, period) -> value

    for rec in extraction.records:
        fund = by_name.get(_norm(rec.fund_ref))
        if fund is None:
            unmatched.add(rec.fund_ref)
            continue
        matched[fund.id] = fund.name
        deduped[(fund.id, rec.period)] = rec.value  # last write wins

    # Upsert per (fund, period) so re-ingesting (or overlapping files) never
    # duplicates observations — last write wins. Duplicates would corrupt the
    # downstream metric math.
    touched = {fund_id for (fund_id, _) in deduped}
    existing = {
        (o.fund_id, o.period): o
        for o in db.scalars(
            select(models.ReturnObservation).where(
                models.ReturnObservation.fund_id.in_(touched)
            )
        )
    }
    for (fund_id, period), value in deduped.items():
        obs = existing.get((fund_id, period))
        if obs is not None:
            obs.value = value
        else:
            db.add(models.ReturnObservation(fund_id=fund_id, period=period, value=value))

    # Record the returns file itself, so the Analyses table can show its name.
    db.add(
        models.SourceFile(
            upload_id=upload_id,
            filename=extraction.source_name,
            kind="returns",
            extraction_path=extraction.shape,
            records_ok=len(deduped),
            records_failed=extraction.report.records_failed,
            report_json=extraction.report.model_dump(mode="json"),
        )
    )
    db.commit()

    periods = [p for (_, p) in deduped]
    return ReturnsIngestResult(
        upload_id=upload_id,
        source_name=extraction.source_name,
        shape=extraction.shape,
        observations_written=len(deduped),
        matched_funds=sorted(set(matched.values())),
        unmatched_refs=sorted(unmatched),
        period_start=min(periods) if periods else None,
        period_end=max(periods) if periods else None,
        report=extraction.report,
    )
