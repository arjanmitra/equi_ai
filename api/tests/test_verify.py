"""Grounding verifier — number extraction + claim verification (hermetic)."""

from __future__ import annotations

import pytest

from app.memo.numbers import extract_numbers
from app.memo.verify import verify_claim, verify_memo
from app.schemas.catalog import Catalog, Fact
from app.schemas.memo import Claim, MemoDraft, MemoSection


# --- Number extraction ------------------------------------------------------
def _one(text):
    toks = extract_numbers(text)
    assert len(toks) == 1, toks
    return toks[0]


def test_extracts_percent():
    t = _one("a fee of 2%")
    assert t.unit == "percent" and 0.02 in t.candidates


def test_extracts_currency_magnitude():
    t = _one("$1.2B in assets")
    assert t.unit == "b" and 1.2e9 in t.candidates


def test_extracts_bps():
    t = _one("150 bps")
    assert t.unit == "bps" and 0.015 in t.candidates


def test_bare_small_integer_is_not_verifiable():
    assert extract_numbers("the top 3 funds")[0].verifiable is False


def test_decimal_and_negative_are_verifiable():
    assert _one("Sharpe of 1.36").verifiable is True
    assert _one("correlation of -0.6").verifiable is True


def test_months_word_not_read_as_millions():
    t = _one("12 months of data")
    assert t.unit is None and t.verifiable is False  # bare small int


# --- Verifier ---------------------------------------------------------------
@pytest.fixture
def catalog():
    facts = [
        Fact(id="metric:f1:sharpe", kind="metric", name="sharpe", label="Sharpe",
             value=1.36, display="1.36", fund_id="f1"),
        Fact(id="metric:f1:annualized_volatility", kind="metric",
             name="annualized_volatility", label="Vol", value=0.181, display="18.1%",
             fund_id="f1"),
        Fact(id="field:f1:management_fee", kind="field", name="management_fee",
             label="Mgmt fee", value=0.02, display="2.0%", fund_id="f1"),
        Fact(id="field:f1:aum_usd", kind="field", name="aum_usd", label="AUM",
             value=1_200_000_000, display="$1.2B", fund_id="f1"),
        Fact(id="field:f1:inception_date", kind="field", name="inception_date",
             label="Inception", value="2018-01-15", display="2018-01-15", fund_id="f1"),
        Fact(id="check:f1:target_volatility", kind="check", name="target_volatility",
             label="Target vol", value="fail", display="vol exceeds target", fund_id="f1",
             extra={"actual": 0.181, "threshold": 0.05}),
    ]
    return Catalog(run_id="r", mandate=[], funds=[], index={f.id: f for f in facts})


def test_grounded_number_passes(catalog):
    c = verify_claim(Claim(text="It posts a Sharpe of 1.36.", refs=["metric:f1:sharpe"]), catalog)
    assert c.verified is True and c.issues == []


def test_rounded_number_still_grounded(catalog):
    # "1.4" rounds from the 1.36 fact -> grounded at the stated precision.
    c = verify_claim(Claim(text="Sharpe near 1.4.", refs=["metric:f1:sharpe"]), catalog)
    assert c.verified is True


def test_hallucinated_number_is_flagged(catalog):
    c = verify_claim(Claim(text="A stellar Sharpe of 2.10.", refs=["metric:f1:sharpe"]), catalog)
    assert c.verified is False
    assert any("ungrounded number" in i for i in c.issues)


def test_percent_and_currency_render_match(catalog):
    assert verify_claim(Claim(text="fee is 2%", refs=["field:f1:management_fee"]), catalog).verified
    assert verify_claim(Claim(text="$1.2B AUM", refs=["field:f1:aum_usd"]), catalog).verified
    assert not verify_claim(Claim(text="$1.5B AUM", refs=["field:f1:aum_usd"]), catalog).verified


def test_check_actual_and_threshold_are_grounded(catalog):
    c = verify_claim(
        Claim(text="volatility 18.1% exceeds the 5.0% target",
              refs=["check:f1:target_volatility"]),
        catalog,
    )
    assert c.verified is True


def test_date_year_is_grounded_by_inception_fact(catalog):
    c = verify_claim(
        Claim(text="launched in 2018", refs=["field:f1:inception_date"]), catalog
    )
    assert c.verified is True


def test_unknown_reference_flagged(catalog):
    c = verify_claim(Claim(text="great fund", refs=["metric:f1:bogus"]), catalog)
    assert c.verified is False
    assert any("unknown reference" in i for i in c.issues)


def test_number_without_any_ref_is_ungrounded(catalog):
    c = verify_claim(Claim(text="Sharpe of 1.36", refs=[]), catalog)
    assert c.verified is False


def test_qualitative_claim_passes(catalog):
    c = verify_claim(Claim(text="The team is experienced.", refs=[]), catalog)
    assert c.verified is True


def test_verify_memo_counts_unverified(catalog):
    draft = MemoDraft(sections=[
        MemoSection(kind="summary", title="Summary", claims=[
            Claim(text="Sharpe of 1.36.", refs=["metric:f1:sharpe"]),
            Claim(text="Sharpe of 9.99.", refs=["metric:f1:sharpe"]),
        ]),
    ])
    vm = verify_memo(draft, catalog)
    assert vm.all_verified is False
    assert len(vm.unverified) == 1
