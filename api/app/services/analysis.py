"""Analysis lifecycle: create, update (as the wizard advances), delete, serialize."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.schemas.analysis import AnalysisOut


def create_analysis(
    db: Session, upload_id: str, label: str | None = None
) -> models.Analysis:
    if label is None:
        upload = db.get(models.Upload, upload_id)
        universe = [s.filename for s in upload.source_files if s.kind == "universe"]
        label = universe[0] if universe else None
    analysis = models.Analysis(upload_id=upload_id, label=label)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def update_analysis(
    db: Session, analysis: models.Analysis, fields: dict
) -> models.Analysis:
    for key, value in fields.items():
        setattr(analysis, key, value)
    db.commit()
    db.refresh(analysis)
    return analysis


def delete_analysis(db: Session, analysis: models.Analysis) -> None:
    # Remove the analysis row first (it FKs the upload/run/memo), then the upload
    # — whose cascade cleans funds, returns, metrics, runs, evaluations, memos.
    upload = db.get(models.Upload, analysis.upload_id)
    db.delete(analysis)
    if upload is not None:
        db.delete(upload)
    db.commit()


def serialize_analysis(analysis: models.Analysis) -> AnalysisOut:
    files = analysis.upload.source_files if analysis.upload else []
    return AnalysisOut(
        id=analysis.id,
        created_at=analysis.created_at,
        label=analysis.label,
        upload_id=analysis.upload_id,
        mandate_id=analysis.mandate_id,
        run_id=analysis.run_id,
        memo_id=analysis.memo_id,
        universe_files=[s.filename for s in files if s.kind == "universe"],
        returns_files=[s.filename for s in files if s.kind == "returns"],
        has_memo=analysis.memo_id is not None,
    )
