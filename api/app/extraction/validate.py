"""Pydantic coercion + sanity checks, splitting hard failures from soft flags."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError

from app.schemas.extraction import IssueLevel, ValidationReport


def coerce_record(
    data: dict[str, Any], target: type[BaseModel]
) -> tuple[BaseModel | None, ValidationError | None]:
    """Try to build a target instance. Returns (instance|None, error|None)."""
    try:
        return target.model_validate(data), None
    except ValidationError as exc:
        return None, exc


def record_sanity_flags(
    record: BaseModel, index: int, report: ValidationReport
) -> None:
    """Soft, domain-aware range checks. Usable-but-suspicious -> FLAG, not drop.

    Kept intentionally small here; metric-stage checks live elsewhere. These are
    cheap signals that the upstream data is probably wrong.
    """
    data = record.model_dump()

    fee = data.get("management_fee")
    if fee is not None and fee > 0.10:
        report.add(
            IssueLevel.FLAG,
            f"management_fee={fee:.2%} is unusually high — check % vs decimal.",
            record_index=index,
            field="management_fee",
        )

    perf = data.get("performance_fee")
    if perf is not None and perf > 0.50:
        report.add(
            IssueLevel.FLAG,
            f"performance_fee={perf:.2%} is unusually high.",
            record_index=index,
            field="performance_fee",
        )

    aum = data.get("aum_usd")
    if aum is not None and aum < 1_000:
        report.add(
            IssueLevel.FLAG,
            f"aum_usd={aum} looks like it may be in millions, not USD.",
            record_index=index,
            field="aum_usd",
        )


def summarize_errors(exc: ValidationError) -> str:
    """Compact, model-friendly rendering of a ValidationError for the repair loop."""
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"])
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)
