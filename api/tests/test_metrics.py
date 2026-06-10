"""Unit tests for the pure metric functions — known sequences, exact answers."""

from __future__ import annotations

import math

import pytest

from datetime import date

from app.metrics import (
    align_series,
    annualized_return,
    annualized_volatility,
    correlation,
    cumulative_return,
    max_drawdown,
    sharpe_ratio,
    summarize_returns,
)


# --- Volatility -------------------------------------------------------------
def test_volatility_of_constant_series_is_zero():
    assert annualized_volatility([0.01] * 6) == pytest.approx(0.0)


def test_volatility_matches_hand_computation():
    # [0.05, -0.05]: sample stdev = sqrt(0.005); annualized * sqrt(12).
    expected = math.sqrt(0.005) * math.sqrt(12)
    assert annualized_volatility([0.05, -0.05]) == pytest.approx(expected)


def test_volatility_requires_two_observations():
    with pytest.raises(ValueError):
        annualized_volatility([0.01])


# --- Max drawdown -----------------------------------------------------------
def test_max_drawdown_finds_worst_trough():
    # cum: 1.1 -> 0.88 -> 0.924; worst dd = 0.88/1.1 - 1 = -0.2.
    assert max_drawdown([0.1, -0.2, 0.05]) == pytest.approx(-0.2)


def test_max_drawdown_is_zero_when_monotonic_up():
    assert max_drawdown([0.01, 0.02, 0.03]) == pytest.approx(0.0)


def test_max_drawdown_is_non_positive():
    assert max_drawdown([-0.1, 0.05, -0.3, 0.2]) <= 0.0


# --- Returns ----------------------------------------------------------------
def test_cumulative_return_compounds():
    assert cumulative_return([0.1, 0.1]) == pytest.approx(0.21)


def test_annualized_return_of_full_year_equals_cumulative():
    # 12 months of constant return: CAGR == cumulative.
    r = [0.01] * 12
    assert annualized_return(r) == pytest.approx(cumulative_return(r))
    assert annualized_return(r) == pytest.approx(1.01**12 - 1)


def test_annualized_return_extrapolates_partial_year():
    # 6 months of +5%: CAGR = (1.05^6)^(12/6) - 1 = 1.05^12 - 1.
    assert annualized_return([0.05] * 6) == pytest.approx(1.05**12 - 1)


def test_annualized_return_handles_wipeout():
    assert annualized_return([-1.0, 0.5]) == pytest.approx(-1.0)


# --- Summary bundle ---------------------------------------------------------
def test_summarize_flags_low_confidence_below_min_obs():
    assert summarize_returns([0.01] * 6).low_confidence is True
    assert summarize_returns([0.01] * 12).low_confidence is False


def test_summarize_empty_series_is_all_none():
    m = summarize_returns([])
    assert m.n_obs == 0
    assert m.annualized_volatility is None
    assert m.max_drawdown is None
    assert m.low_confidence is True


def test_summarize_single_observation_has_no_volatility():
    m = summarize_returns([0.02])
    assert m.n_obs == 1
    assert m.annualized_volatility is None  # needs >= 2
    assert m.max_drawdown == pytest.approx(0.0)
    assert m.cumulative_return == pytest.approx(0.02)


# --- Sharpe -----------------------------------------------------------------
def test_sharpe_matches_definition():
    r = [0.02, -0.01, 0.03, 0.0, 0.01, -0.02]
    expected = (annualized_return(r) - 0.03) / annualized_volatility(r)
    assert sharpe_ratio(r, 0.03) == pytest.approx(expected)


def test_higher_risk_free_lowers_sharpe():
    r = [0.02, -0.01, 0.03, 0.0, 0.01, -0.02]
    assert sharpe_ratio(r, 0.05) < sharpe_ratio(r, 0.0)


def test_sharpe_undefined_for_zero_volatility():
    with pytest.raises(ValueError):
        sharpe_ratio([0.01, 0.01, 0.01], 0.0)


# --- Correlation + alignment ------------------------------------------------
def test_correlation_perfect_positive_and_negative():
    a = [0.01, 0.02, 0.03, 0.04]
    assert correlation(a, [0.02, 0.04, 0.06, 0.08]) == pytest.approx(1.0)
    assert correlation(a, [-0.01, -0.02, -0.03, -0.04]) == pytest.approx(-1.0)


def test_correlation_requires_equal_length():
    with pytest.raises(ValueError):
        correlation([0.01, 0.02], [0.01])


def test_align_series_intersects_on_common_periods():
    a = {date(2023, 1, 1): 0.1, date(2023, 2, 1): 0.2, date(2023, 3, 1): 0.3}
    b = {date(2023, 2, 1): 0.5, date(2023, 3, 1): 0.6, date(2023, 4, 1): 0.7}
    fa, fb = align_series(a, b)
    assert fa == [0.2, 0.3]  # chronological, common months only
    assert fb == [0.5, 0.6]
