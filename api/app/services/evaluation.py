"""Mandate persistence + running an evaluation over a persisted upload.

`run_mandate` evaluates every fund in an upload against a mandate (the pure
constraint engine does the judging) and persists one FundEvaluation per fund.
`serialize_run` turns a run into the ranked API response (passed first, then by
score descending).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constraints import evaluate
from app.db import models
from app.schemas.evaluation import ConstraintCheck, FundEvaluationOut, RunOut
from app.schemas.mandate import MandateSpec


def create_mandate(db: Session, spec: MandateSpec) -> models.Mandate:
    mandate = models.Mandate(label=spec.label, spec_json=spec.model_dump(mode="json"))
    db.add(mandate)
    db.commit()
    db.refresh(mandate)
    return mandate


def run_mandate(
    db: Session,
    upload_id: str,
    mandate: models.Mandate,
    today: date | None = None,
) -> models.MandateRun:
    spec = MandateSpec.model_validate(mandate.spec_json)
    run = models.MandateRun(upload_id=upload_id, mandate_id=mandate.id)
    db.add(run)
    db.flush()  # assign run.id

    funds = db.scalars(
        select(models.Fund).where(models.Fund.upload_id == upload_id)
    ).all()
    for fund in funds:
        # The engine reads attributes by name, so the ORM Fund works directly.
        ev = evaluate(fund, spec, today=today)
        db.add(
            models.FundEvaluation(
                mandate_run_id=run.id,
                fund_id=fund.id,
                passed=ev.passed,
                score=ev.score,
                checks_json=[c.model_dump(mode="json") for c in ev.checks],
            )
        )

    db.commit()
    db.refresh(run)
    return run


def serialize_run(run: models.MandateRun) -> RunOut:
    evaluations = [
        FundEvaluationOut(
            fund_id=fe.fund_id,
            fund_name=fe.fund.name,
            business_key=fe.fund.business_key,
            passed=fe.passed,
            score=fe.score,
            checks=[ConstraintCheck.model_validate(c) for c in fe.checks_json],
        )
        for fe in run.evaluations
    ]
    # Shortlist on top: passed funds first, then by score descending.
    evaluations.sort(key=lambda e: (e.passed, e.score), reverse=True)
    return RunOut(
        id=run.id,
        upload_id=run.upload_id,
        mandate_id=run.mandate_id,
        created_at=run.created_at,
        evaluations=evaluations,
    )
