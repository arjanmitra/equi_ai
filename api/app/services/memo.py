"""Generate + persist an IC memo, and serialize it for the audit view.

Generation runs the verifier loop; persistence stores sections/claims with their
refs and verification verdict. Serialization rebuilds the catalog from the run
to resolve each cited ref to its fact and to build the deterministic appendix —
so the memo stays the source of truth for prose, and the run for the numbers.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.db import models
from app.memo import build_catalog, generate_memo
from app.schemas.memo import MemoClaimOut, MemoOut, MemoSectionOut


def generate_and_persist_memo(db: Session, run: models.MandateRun) -> models.Memo:
    catalog = build_catalog(run)
    verified, log = generate_memo(catalog)

    memo = models.Memo(
        mandate_run_id=run.id,
        model=settings.memo_model,
        all_verified=verified.all_verified,
        log_json=log,
    )
    db.add(memo)
    db.flush()

    for si, section in enumerate(verified.sections):
        sec = models.MemoSection(
            memo_id=memo.id, kind=section.kind, title=section.title, position=si
        )
        db.add(sec)
        db.flush()
        for ci, claim in enumerate(section.claims):
            db.add(
                models.MemoClaim(
                    section_id=sec.id,
                    position=ci,
                    text=claim.text,
                    refs_json=claim.refs,
                    verified=claim.verified,
                    issues_json=claim.issues,
                )
            )

    db.commit()
    db.refresh(memo)
    return memo


def serialize_memo(memo: models.Memo) -> MemoOut:
    catalog = build_catalog(memo.run)

    sections: list[MemoSectionOut] = []
    ref_ids: set[str] = set()
    for section in sorted(memo.sections, key=lambda s: s.position):
        claims = []
        for claim in sorted(section.claims, key=lambda c: c.position):
            ref_ids.update(claim.refs_json or [])
            claims.append(
                MemoClaimOut(
                    id=claim.id,
                    text=claim.text,
                    refs=claim.refs_json or [],
                    verified=claim.verified,
                    issues=claim.issues_json or [],
                )
            )
        sections.append(
            MemoSectionOut(kind=section.kind, title=section.title, claims=claims)
        )

    facts = {rid: catalog.resolve(rid) for rid in ref_ids if catalog.resolve(rid)}

    return MemoOut(
        id=memo.id,
        run_id=memo.mandate_run_id,
        created_at=memo.created_at,
        model=memo.model,
        all_verified=memo.all_verified,
        log=memo.log_json or [],
        sections=sections,
        facts=facts,
        appendix=catalog.funds,
    )
