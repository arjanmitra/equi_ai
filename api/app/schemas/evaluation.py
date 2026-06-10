"""Result types for evaluating a fund against a mandate.

A FundEvaluation is a list of per-constraint checks plus a verdict and a score.
Every check is deterministic, carries a human-readable `reason`, and names the
fund `source_fields` it judged — so the verdict is explainable and traceable
(those reasons later become grounded claims in the memo, never LLM inventions).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.mandate import MandateSpec


class ConstraintId(str, Enum):
    EXCLUDED_STRATEGY = "excluded_strategy"
    REDEMPTION_FREQUENCY = "redemption_frequency"
    NOTICE_PERIOD = "notice_period"
    LOCKUP = "lockup"
    PREFERRED_STRATEGY = "preferred_strategy"
    MANAGEMENT_FEE = "management_fee"
    PERFORMANCE_FEE = "performance_fee"
    MIN_AUM = "min_aum"
    MIN_TRACK_RECORD = "min_track_record"
    TARGET_VOLATILITY = "target_volatility"
    MAX_DRAWDOWN = "max_drawdown"


class Severity(str, Enum):
    HARD = "hard"  # violation eliminates the fund from the shortlist
    SOFT = "soft"  # violation applies a score penalty but keeps the fund


class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NA = "na"  # not evaluable (missing fund data, or pending metrics)


class ConstraintCheck(BaseModel):
    constraint: ConstraintId
    severity: Severity
    status: CheckStatus
    actual: Any | None = None
    threshold: Any | None = None
    penalty: float = 0.0
    reason: str
    source_fields: list[str] = Field(
        default_factory=list,
        description="Fund fields this check judged (for audit linkage).",
    )


class FundEvaluation(BaseModel):
    passed: bool  # no hard violation
    score: float  # 100 minus soft penalties, clamped to [0, 100]
    checks: list[ConstraintCheck]


# --- API read-models --------------------------------------------------------
class MandateOut(BaseModel):
    id: str
    created_at: datetime
    label: str | None
    spec: MandateSpec


class FundEvaluationOut(BaseModel):
    fund_id: str
    fund_name: str
    business_key: str
    passed: bool
    score: float
    checks: list[ConstraintCheck]


class RunOut(BaseModel):
    id: str
    upload_id: str
    mandate_id: str
    created_at: datetime
    evaluations: list[FundEvaluationOut]  # ranked: passed first, then score desc
