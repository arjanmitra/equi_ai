"""Persist ExtractionResults into the relational audit model.

One Upload per /extract call; one SourceFile per result; one Fund per record;
one SourceField per provenance entry. Provenance is linked to its Fund via the
record_index (which now aligns with the compacted records list — see the
tabular mapper). The whole batch is one transaction.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.db import models
from app.schemas.extraction import ExtractionResult


def _to_date(value) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def save_extraction(
    db: Session,
    results: list[ExtractionResult],
    *,
    label: str | None = None,
) -> models.Upload:
    """Write an Upload and all of its files/funds/provenance; return the Upload."""
    upload = models.Upload(label=label)
    db.add(upload)
    db.flush()  # assign upload.id

    for result in results:
        source_file = models.SourceFile(
            upload_id=upload.id,
            filename=result.source_name,
            mime=result.mime,
            extraction_path=result.strategy,
            records_ok=result.report.records_ok,
            records_failed=result.report.records_failed,
            report_json=result.report.model_dump(mode="json"),
        )
        db.add(source_file)
        db.flush()  # assign source_file.id

        # records list position -> persisted Fund row
        index_to_fund: dict[int, models.Fund] = {}
        for idx, rec in enumerate(result.records):
            fund = models.Fund(
                upload_id=upload.id,
                source_file_id=source_file.id,
                business_key=rec.get("fund_id") or "",
                name=rec.get("name") or "",
                strategy=rec.get("strategy"),
                redemption_frequency=rec.get("redemption_frequency"),
                notice_period_days=rec.get("notice_period_days"),
                lockup_months=rec.get("lockup_months"),
                management_fee=rec.get("management_fee"),
                performance_fee=rec.get("performance_fee"),
                aum_usd=rec.get("aum_usd"),
                inception_date=_to_date(rec.get("inception_date")),
                notes=rec.get("notes"),
            )
            db.add(fund)
            db.flush()
            index_to_fund[idx] = fund

        for prov in result.provenance:
            fund = index_to_fund.get(prov.record_index)
            if fund is None:
                continue  # provenance for a dropped/unknown record — skip
            pj = prov.model_dump(mode="json")  # JSON-safe (dates -> iso, etc.)
            db.add(
                models.SourceField(
                    fund_id=fund.id,
                    target_field=prov.target_field,
                    raw_value=None if pj["raw_value"] is None else str(pj["raw_value"]),
                    normalized_value=pj["normalized_value"],
                    source=prov.source,
                    transform=prov.transform,
                    confidence=prov.confidence,
                )
            )

    db.commit()
    db.refresh(upload)
    return upload
