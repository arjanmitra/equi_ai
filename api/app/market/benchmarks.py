"""Strategy -> benchmark mapping.

Sensible default index per strategy, overridable per request. Where the public
proxy is a weak fit (macro, managed futures, etc.) we attach a note rather than
pretend the comparison is clean — a domain-honesty signal that surfaces in the
metrics' audit record.
"""

from __future__ import annotations

_STRATEGY_BENCHMARKS: dict[str, str] = {
    "long_short_equity": "SPY",
    "event_driven": "SPY",
    "market_neutral": "SPY",
    "global_macro": "SPY",
    "managed_futures": "SPY",
    "multi_strategy": "SPY",
    "credit": "AGG",
    "relative_value": "AGG",
    "fixed_income": "AGG",
    "other": "SPY",
}

# Strategies whose default public benchmark is a weak proxy.
_WEAK_FIT = {"global_macro", "managed_futures", "market_neutral", "multi_strategy"}

_DEFAULT = "SPY"


def benchmark_for(
    strategy: str | None, overrides: dict[str, str] | None = None
) -> tuple[str, str | None]:
    """Return (ticker, note). `overrides` maps strategy -> ticker and wins."""
    overrides = overrides or {}
    if strategy and strategy in overrides:
        return overrides[strategy], None
    ticker = _STRATEGY_BENCHMARKS.get(strategy or "", _DEFAULT)
    note = (
        f"{ticker} is a weak public proxy for {strategy}"
        if strategy in _WEAK_FIT
        else None
    )
    return ticker, note
