"""Pure, deterministic metric functions over a monthly return series.

Conventions (stated explicitly — they are exactly what a reviewer will ask about):
  - Inputs are decimal monthly returns (0.012 = +1.2%).
  - Volatility is annualized: sample stdev (ddof=1) * sqrt(12).
  - Annualized return is the geometric CAGR, not an arithmetic mean.
  - Max drawdown is the worst peak-to-trough of the cumulative curve, <= 0.
  - Below MIN_OBS observations, results are flagged low-confidence (still computed).

Hand-rolled rather than pulled from a library so the assumptions are visible and
testable. Sharpe and correlation need a benchmark + risk-free rate and arrive in
a later step.
"""

from __future__ import annotations

import math
import statistics
from datetime import date

from app.schemas.metrics import PartialMetrics

PERIODS_PER_YEAR = 12
MIN_OBS = 12  # ~1 year of monthly data before vol/Sharpe are trustworthy


def _growth(returns: list[float]) -> float:
    g = 1.0
    for r in returns:
        g *= 1.0 + r
    return g


def annualized_volatility(returns: list[float]) -> float:
    if len(returns) < 2:
        raise ValueError("annualized_volatility needs >= 2 observations")
    return statistics.stdev(returns) * math.sqrt(PERIODS_PER_YEAR)


def max_drawdown(returns: list[float]) -> float:
    """Worst peak-to-trough decline of the cumulative curve. Returns <= 0."""
    if not returns:
        raise ValueError("max_drawdown needs >= 1 observation")
    cum = peak = 1.0
    mdd = 0.0
    for r in returns:
        cum *= 1.0 + r
        peak = max(peak, cum)
        mdd = min(mdd, cum / peak - 1.0)
    return mdd


def cumulative_return(returns: list[float]) -> float:
    if not returns:
        raise ValueError("cumulative_return needs >= 1 observation")
    return _growth(returns) - 1.0


def annualized_return(returns: list[float]) -> float:
    """Geometric CAGR. Guards against a wipeout (growth <= 0) -> total loss."""
    if not returns:
        raise ValueError("annualized_return needs >= 1 observation")
    g = _growth(returns)
    if g <= 0:
        return -1.0
    return g ** (PERIODS_PER_YEAR / len(returns)) - 1.0


def sharpe_ratio(returns: list[float], rf_annual: float) -> float:
    """Annualized Sharpe: (CAGR - annual risk-free) / annualized vol."""
    if len(returns) < 2:
        raise ValueError("sharpe_ratio needs >= 2 observations")
    vol = annualized_volatility(returns)
    if vol == 0:
        raise ValueError("sharpe_ratio undefined for zero volatility")
    return (annualized_return(returns) - rf_annual) / vol


def correlation(a: list[float], b: list[float]) -> float:
    """Pearson correlation of two equal-length, aligned return series."""
    if len(a) != len(b):
        raise ValueError("correlation needs equal-length series")
    if len(a) < 2:
        raise ValueError("correlation needs >= 2 observations")
    return statistics.correlation(a, b)


def align_series(
    a: dict[date, float], b: dict[date, float]
) -> tuple[list[float], list[float]]:
    """Values of a and b over their common periods, in chronological order."""
    common = sorted(set(a) & set(b))
    return [a[p] for p in common], [b[p] for p in common]


def summarize_returns(returns: list[float]) -> PartialMetrics:
    """Bundle the return-only metrics, applying the min-obs policy."""
    n = len(returns)
    return PartialMetrics(
        n_obs=n,
        annualized_volatility=annualized_volatility(returns) if n >= 2 else None,
        max_drawdown=max_drawdown(returns) if n >= 1 else None,
        annualized_return=annualized_return(returns) if n >= 1 else None,
        cumulative_return=cumulative_return(returns) if n >= 1 else None,
        low_confidence=n < MIN_OBS,
    )
