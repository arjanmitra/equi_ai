"""The grounding catalog: the set of facts a memo is allowed to cite.

Every fact has a stable ID (the citation target). The catalog is both the
structured input the LLM sees and the whitelist the verifier checks claims
against — a claim may only reference IDs that exist here, and any number in its
prose must match a cited fact's value.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

FactKind = Literal["field", "metric", "check", "mandate"]


class Fact(BaseModel):
    id: str  # e.g. "metric:<fund_id>:sharpe"
    kind: FactKind
    name: str  # field/metric/constraint key
    label: str  # human label, e.g. "Sharpe ratio"
    value: Any = None  # canonical value (number/str) for the verifier to match
    display: str  # formatted for humans / the appendix
    fund_id: str | None = None
    provenance: str | None = None  # where it came from (column, metric basis, …)
    extra: dict = Field(default_factory=dict)  # raw value, check actual/threshold, …


class FundFacts(BaseModel):
    fund_id: str
    fund_name: str
    business_key: str
    rank: int
    passed: bool
    score: float
    fields: list[Fact]
    metrics: list[Fact]
    checks: list[Fact]


class Catalog(BaseModel):
    run_id: str
    mandate: list[Fact]
    funds: list[FundFacts]  # ranked
    index: dict[str, Fact]  # every fact, flattened, for resolution/validation

    def resolve(self, fact_id: str) -> Fact | None:
        return self.index.get(fact_id)

    @property
    def valid_ids(self) -> set[str]:
        return set(self.index.keys())
