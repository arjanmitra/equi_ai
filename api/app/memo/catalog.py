"""Assemble the grounding catalog from a MandateRun.

Pulls together, for each fund: its canonical fields (with SourceField
provenance), its computed metrics (with their inputs as provenance), and its
constraint-check results — plus the mandate's thresholds. Each becomes a Fact
with a stable ID. Funds are ranked the same way the run results are.
"""

from __future__ import annotations

from typing import Any, Callable

from app.db import models
from app.schemas.catalog import Catalog, Fact, FundFacts


# --- Fact ID scheme ---------------------------------------------------------
def field_id(fund_id: str, name: str) -> str:
    return f"field:{fund_id}:{name}"


def metric_id(fund_id: str, name: str) -> str:
    return f"metric:{fund_id}:{name}"


def check_id(fund_id: str, constraint: str) -> str:
    return f"check:{fund_id}:{constraint}"


def mandate_id(name: str) -> str:
    return f"mandate:{name}"


# --- Display formatting -----------------------------------------------------
def _pct(v: Any) -> str:
    return f"{v * 100:.1f}%" if isinstance(v, (int, float)) else str(v)


def _money(v: Any) -> str:
    try:
        return f"${float(v):,.0f}"
    except (TypeError, ValueError):
        return str(v)


def _num(v: Any) -> str:
    return f"{v:.2f}" if isinstance(v, (int, float)) else str(v)


def _days(v: Any) -> str:
    return f"{v} days"


def _months(v: Any) -> str:
    return f"{v} months"


def _ident(v: Any) -> str:
    return "—" if v is None else str(v)


_FIELD_FMT: dict[str, tuple[str, Callable]] = {
    "name": ("Fund name", _ident),
    "fund_id": ("Fund id", _ident),
    "strategy": ("Strategy", _ident),
    "redemption_frequency": ("Redemption frequency", _ident),
    "notice_period_days": ("Notice period", _days),
    "lockup_months": ("Lockup", _months),
    "management_fee": ("Management fee", _pct),
    "performance_fee": ("Performance fee", _pct),
    "aum_usd": ("AUM", _money),
    "inception_date": ("Inception date", _ident),
    "notes": ("Notes", _ident),
}

_METRIC_SPECS: list[tuple[str, str, Callable]] = [
    ("annualized_volatility", "Volatility (annualized)", _pct),
    ("max_drawdown", "Max drawdown", _pct),
    ("annualized_return", "Annualized return (CAGR)", _pct),
    ("cumulative_return", "Cumulative return", _pct),
    ("sharpe", "Sharpe ratio", _num),
    ("correlation_benchmark", "Correlation to benchmark", _num),
    ("n_obs", "Months of data", _ident),
    ("benchmark_ticker", "Benchmark", _ident),
]

_MANDATE_SPECS: dict[str, tuple[str, Callable]] = {
    "max_redemption_frequency": ("Required redemption frequency", _ident),
    "max_notice_period_days": ("Max notice period", _days),
    "max_lockup_months": ("Max lockup", _months),
    "max_management_fee": ("Max management fee", _pct),
    "max_performance_fee": ("Max performance fee", _pct),
    "min_aum_usd": ("Min AUM", _money),
    "min_track_record_months": ("Min track record", _months),
    "target_volatility": ("Target volatility", _pct),
    "max_drawdown": ("Max drawdown tolerance", _pct),
}

_CONSTRAINT_LABELS: dict[str, str] = {
    "excluded_strategy": "Excluded strategy",
    "redemption_frequency": "Liquidity (redemption)",
    "notice_period": "Notice period",
    "lockup": "Lockup",
    "preferred_strategy": "Strategy preference",
    "management_fee": "Management fee",
    "performance_fee": "Performance fee",
    "min_aum": "Minimum AUM",
    "min_track_record": "Track record",
    "target_volatility": "Target volatility",
    "max_drawdown": "Max drawdown",
}


def _metric_provenance(m: models.FundMetrics) -> str | None:
    i = m.inputs_json or {}
    parts: list[str] = []
    if i.get("n_obs"):
        parts.append(f"{i['n_obs']} monthly returns")
    if i.get("period_start"):
        parts.append(f"{i['period_start']}–{i.get('period_end')}")
    if i.get("benchmark_ticker"):
        parts.append(f"vs {i['benchmark_ticker']}")
    if i.get("risk_free_ticker"):
        parts.append(f"rf {i['risk_free_ticker']}")
    return ", ".join(parts) or None


# --- Fact builders ----------------------------------------------------------
def _field_facts(fund: models.Fund) -> list[Fact]:
    facts: list[Fact] = []
    seen: set[str] = set()
    for sf in fund.source_fields:
        if sf.target_field in seen:
            continue
        seen.add(sf.target_field)
        label, fmt = _FIELD_FMT.get(sf.target_field, (sf.target_field, _ident))
        facts.append(
            Fact(
                id=field_id(fund.id, sf.target_field),
                kind="field",
                name=sf.target_field,
                label=label,
                value=sf.normalized_value,
                display=fmt(sf.normalized_value) if sf.normalized_value is not None else "—",
                fund_id=fund.id,
                provenance=sf.source,
                extra={"raw": sf.raw_value},
            )
        )
    return facts


def _metric_facts(fund: models.Fund) -> list[Fact]:
    m = fund.metrics
    if m is None:
        return []
    prov = _metric_provenance(m)
    facts: list[Fact] = []
    for attr, label, fmt in _METRIC_SPECS:
        value = getattr(m, attr)
        if value is None:
            continue
        facts.append(
            Fact(
                id=metric_id(fund.id, attr),
                kind="metric",
                name=attr,
                label=label,
                value=value,
                display=fmt(value),
                fund_id=fund.id,
                provenance=prov,
                extra={"low_confidence": m.low_confidence},
            )
        )
    return facts


def _check_facts(fund: models.Fund, ev: models.FundEvaluation) -> list[Fact]:
    facts: list[Fact] = []
    for c in ev.checks_json or []:
        cid = c["constraint"]
        facts.append(
            Fact(
                id=check_id(fund.id, cid),
                kind="check",
                name=cid,
                label=_CONSTRAINT_LABELS.get(cid, cid),
                value=c["status"],
                display=c["reason"],
                fund_id=fund.id,
                extra={
                    "status": c["status"],
                    "severity": c["severity"],
                    "actual": c.get("actual"),
                    "threshold": c.get("threshold"),
                },
            )
        )
    return facts


def _mandate_facts(spec: dict) -> list[Fact]:
    facts: list[Fact] = []
    for key, (label, fmt) in _MANDATE_SPECS.items():
        value = spec.get(key)
        if value is None:
            continue
        facts.append(
            Fact(id=mandate_id(key), kind="mandate", name=key, label=label,
                 value=value, display=fmt(value), provenance="mandate")
        )
    for key in ("preferred_strategies", "excluded_strategies"):
        vals = spec.get(key) or []
        if vals:
            facts.append(
                Fact(id=mandate_id(key), kind="mandate", name=key,
                     label=key.replace("_", " ").title(), value=vals,
                     display=", ".join(vals), provenance="mandate")
            )
    return facts


def build_catalog(run: models.MandateRun) -> Catalog:
    index: dict[str, Fact] = {}

    mandate_facts = _mandate_facts(run.mandate.spec_json or {})
    for f in mandate_facts:
        index[f.id] = f

    def rank_key(ev: models.FundEvaluation):
        m = ev.fund.metrics
        sharpe = m.sharpe if (m and m.sharpe is not None) else float("-inf")
        return (ev.passed, ev.score, sharpe)

    evaluations = sorted(run.evaluations, key=rank_key, reverse=True)

    funds: list[FundFacts] = []
    for rank, ev in enumerate(evaluations, start=1):
        fund = ev.fund
        fields = _field_facts(fund)
        metrics = _metric_facts(fund)
        checks = _check_facts(fund, ev)
        for f in (*fields, *metrics, *checks):
            index[f.id] = f
        funds.append(
            FundFacts(
                fund_id=fund.id, fund_name=fund.name, business_key=fund.business_key,
                rank=rank, passed=ev.passed, score=ev.score,
                fields=fields, metrics=metrics, checks=checks,
            )
        )

    return Catalog(run_id=run.id, mandate=mandate_facts, funds=funds, index=index)
