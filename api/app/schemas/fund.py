"""The canonical fund-universe schema.

This is the *target* every messy input gets mapped onto. It is the single most
important contract in Option B: lock it down early, keep extraction adaptive but
always aimed here. Field `description`s double as hints to the LLM mapper and to
the heuristic fallback, so write them for a reader who has never seen the source.
"""

from __future__ import annotations

import re
from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


class Strategy(str, Enum):
    LONG_SHORT_EQUITY = "long_short_equity"
    MARKET_NEUTRAL = "market_neutral"
    GLOBAL_MACRO = "global_macro"
    MANAGED_FUTURES = "managed_futures"
    EVENT_DRIVEN = "event_driven"
    CREDIT = "credit"
    RELATIVE_VALUE = "relative_value"
    MULTI_STRATEGY = "multi_strategy"
    FIXED_INCOME = "fixed_income"
    OTHER = "other"


class RedemptionFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"
    OTHER = "other"


# Free-text -> enum aliases. Keys are normalized via _norm (lowercased, alnum).
_STRATEGY_ALIASES: dict[str, Strategy] = {
    "l s equity": Strategy.LONG_SHORT_EQUITY,
    "long short equity": Strategy.LONG_SHORT_EQUITY,
    "long short": Strategy.LONG_SHORT_EQUITY,
    "equity l s": Strategy.LONG_SHORT_EQUITY,
    "market neutral": Strategy.MARKET_NEUTRAL,
    "macro": Strategy.GLOBAL_MACRO,
    "global macro": Strategy.GLOBAL_MACRO,
    "cta": Strategy.MANAGED_FUTURES,
    "managed futures": Strategy.MANAGED_FUTURES,
    "cta managed futures": Strategy.MANAGED_FUTURES,
    "trend following": Strategy.MANAGED_FUTURES,
    "event driven": Strategy.EVENT_DRIVEN,
    "credit": Strategy.CREDIT,
    "credit opportunities": Strategy.CREDIT,
    "relative value": Strategy.RELATIVE_VALUE,
    "multi strategy": Strategy.MULTI_STRATEGY,
    "multi strat": Strategy.MULTI_STRATEGY,
    "fixed income": Strategy.FIXED_INCOME,
}

_REDEMPTION_ALIASES: dict[str, RedemptionFrequency] = {
    "daily": RedemptionFrequency.DAILY,
    "weekly": RedemptionFrequency.WEEKLY,
    "monthly": RedemptionFrequency.MONTHLY,
    "quarterly": RedemptionFrequency.QUARTERLY,
    "semi annual": RedemptionFrequency.SEMI_ANNUAL,
    "semi annually": RedemptionFrequency.SEMI_ANNUAL,
    "annual": RedemptionFrequency.ANNUAL,
    "annually": RedemptionFrequency.ANNUAL,
    "yearly": RedemptionFrequency.ANNUAL,
}


def _coerce_enum(value, aliases: dict, enum_cls):
    """Map messy free text onto an enum member; unknown non-empty -> OTHER."""
    if value is None or isinstance(value, enum_cls):
        return value
    key = _norm(value)
    if not key:
        return None
    if key in aliases:
        return aliases[key]
    # Direct match against an enum value (e.g. "monthly", "global_macro").
    for member in enum_cls:
        if key.replace(" ", "_") == member.value or key == member.value:
            return member
    return enum_cls.OTHER


class Fund(BaseModel):
    """One row of the canonical fund universe."""

    model_config = ConfigDict(use_enum_values=True)

    fund_id: str | None = Field(
        default=None,
        description="Stable identifier for the fund. If the source has no id, "
        "it is auto-derived from a slug of the fund name.",
    )
    name: str = Field(description="Human-readable fund or manager name.")
    strategy: Strategy = Field(
        default=Strategy.OTHER,
        description="Investment strategy bucket. Map free-text strategies "
        "(e.g. 'L/S equity', 'CTA', 'macro') onto the closest enum value.",
    )

    # --- Liquidity terms ---
    redemption_frequency: RedemptionFrequency | None = Field(
        default=None,
        description="How often investors can redeem (daily/monthly/quarterly/...).",
    )
    notice_period_days: int | None = Field(
        default=None,
        ge=0,
        description="Redemption notice period in days.",
    )
    lockup_months: int | None = Field(
        default=None,
        ge=0,
        description="Initial lockup period in months (0 if none).",
    )

    # --- Fee terms (stored as decimals: 2% -> 0.02) ---
    management_fee: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Annual management fee as a decimal. '2%' -> 0.02.",
    )
    performance_fee: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Performance/incentive fee as a decimal. '20%' -> 0.20.",
    )

    # --- Summary stats ---
    aum_usd: float | None = Field(
        default=None,
        ge=0,
        description="Assets under management in USD (absolute, not millions).",
    )
    inception_date: date | None = Field(
        default=None, description="Fund inception/launch date."
    )

    # --- Qualitative ---
    notes: str | None = Field(
        default=None,
        description="Free-text qualitative notes (team changes, key-person "
        "risk, etc.).",
    )

    @field_validator("strategy", mode="before")
    @classmethod
    def _coerce_strategy(cls, v):
        return _coerce_enum(v, _STRATEGY_ALIASES, Strategy) or Strategy.OTHER

    @field_validator("redemption_frequency", mode="before")
    @classmethod
    def _coerce_redemption(cls, v):
        return _coerce_enum(v, _REDEMPTION_ALIASES, RedemptionFrequency)

    @field_validator("name")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("must not be empty")
        return v

    @model_validator(mode="after")
    def _derive_fund_id(self) -> "Fund":
        if not (self.fund_id and self.fund_id.strip()):
            self.fund_id = _slug(self.name)
        return self
