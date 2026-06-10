"""Memo claim schemas.

`MemoDraft` is what the LLM emits: sections of claims, each claim carrying the
fact IDs (`refs`) it rests on. `VerifiedMemo` is the draft after the grounding
verifier has checked every claim — unverified claims keep a list of issues and
are flagged (not dropped), per the flag-and-show decision.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.catalog import Fact, FundFacts

SectionKind = Literal["summary", "recommendation", "risks"]


class Claim(BaseModel):
    text: str
    refs: list[str] = Field(
        default_factory=list, description="Fact IDs from the catalog this claim cites."
    )


class MemoSection(BaseModel):
    kind: SectionKind
    title: str
    claims: list[Claim]


class MemoDraft(BaseModel):
    sections: list[MemoSection]


class VerifiedClaim(BaseModel):
    text: str
    refs: list[str]
    verified: bool
    issues: list[str] = Field(default_factory=list)


class VerifiedSection(BaseModel):
    kind: str
    title: str
    claims: list[VerifiedClaim]


class VerifiedMemo(BaseModel):
    sections: list[VerifiedSection]

    @property
    def unverified(self) -> list[VerifiedClaim]:
        return [c for s in self.sections for c in s.claims if not c.verified]

    @property
    def all_verified(self) -> bool:
        return not self.unverified


# --- API read-models --------------------------------------------------------
class MemoClaimOut(BaseModel):
    id: str
    text: str
    refs: list[str]
    verified: bool
    issues: list[str]


class MemoSectionOut(BaseModel):
    kind: str
    title: str
    claims: list[MemoClaimOut]


class MemoOut(BaseModel):
    id: str
    run_id: str
    created_at: datetime
    model: str
    all_verified: bool
    log: list[str]
    sections: list[MemoSectionOut]
    facts: dict[str, Fact]  # resolved citations across all claims
    appendix: list[FundFacts]  # deterministic per-fund table
