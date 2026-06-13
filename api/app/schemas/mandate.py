"""The mandate: the allocator's constraints, validated from the form.

Persisted as a JSON blob (Mandate.spec_json) and mirrored by zod on the
frontend. The risk constraints (target_volatility, max_drawdown) are captured
here but not yet evaluated — they need the metrics stage, so the engine reports
them as `na` ("pending metrics") for now.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.fund import RedemptionFrequency, Strategy


class MandateSpec(BaseModel):
    label: str | None = Field(default=None, description="Human label for the mandate.")

    # --- Liquidity (hard constraints) ---
    max_redemption_frequency: RedemptionFrequency | None = Field(
        default=None,
        description="Least-liquid redemption frequency that is acceptable "
        "(e.g. 'quarterly' = need at least quarterly liquidity).",
    )
    max_notice_period_days: int | None = Field(default=None, ge=0)
    max_lockup_months: int | None = Field(default=None, ge=0)

    # --- Fees (soft constraints) ---
    max_management_fee: float | None = Field(default=None, ge=0, le=1)
    max_performance_fee: float | None = Field(default=None, ge=0, le=1)

    # --- Strategy (exclusions hard, preferences soft) ---
    preferred_strategies: list[Strategy] = Field(default_factory=list)
    excluded_strategies: list[Strategy] = Field(default_factory=list)

    # --- Size / track record (soft constraints) ---
    min_aum_usd: float | None = Field(default=None, ge=0)
    min_track_record_months: int | None = Field(default=None, ge=0)

    # --- Risk (modeled now, evaluated once metrics exist) ---
    target_volatility: float | None = Field(
        default=None, ge=0, description="Max acceptable annualized volatility."
    )
    max_drawdown: float | None = Field(
        default=None, ge=0, description="Max acceptable peak-to-trough drawdown."
    )

    # --- Per-constraint policy overrides (keyed by ConstraintId value) ---
    # Severity: whether a violation eliminates ("hard") or just penalizes
    # ("soft"). Penalty: the soft-violation score deduction (out of 100).
    # Both fall back to the engine's defaults when a constraint is absent.
    severities: dict[str, Literal["hard", "soft"]] = Field(default_factory=dict)
    penalties: dict[str, float] = Field(default_factory=dict)
