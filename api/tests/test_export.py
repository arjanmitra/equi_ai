"""Memo export rendering (hermetic — hand-built MemoOut, no DB/LLM)."""

from __future__ import annotations

from datetime import datetime

from app.schemas.catalog import Fact, FundFacts
from app.schemas.memo import MemoClaimOut, MemoOut, MemoSectionOut
from app.services.export import memo_to_docx, memo_to_pdf


def _memo_out() -> MemoOut:
    sharpe = Fact(id="metric:f1:sharpe", kind="metric", name="sharpe", label="Sharpe",
                  value=1.36, display="1.36", fund_id="f1")
    appendix = [
        FundFacts(
            fund_id="f1", fund_name="Alpha Macro", business_key="alpha-macro",
            rank=1, passed=True, score=90.0,
            fields=[
                Fact(id="field:f1:strategy", kind="field", name="strategy",
                     label="Strategy", value="global_macro", display="global_macro", fund_id="f1"),
                Fact(id="field:f1:aum_usd", kind="field", name="aum_usd", label="AUM",
                     value=1.2e9, display="$1,200,000,000", fund_id="f1"),
            ],
            metrics=[
                sharpe,
                Fact(id="metric:f1:annualized_volatility", kind="metric",
                     name="annualized_volatility", label="Vol", value=0.18,
                     display="18.0%", fund_id="f1"),
            ],
            checks=[],
        )
    ]
    return MemoOut(
        id="m1", run_id="r1", created_at=datetime(2024, 1, 1), model="claude-opus-4-8",
        all_verified=False, log=["attempt 1: 1 ungrounded claim(s)"],
        sections=[
            MemoSectionOut(kind="summary", title="Summary", claims=[
                # Curly quotes/en dash to exercise the latin-1 sanitizer.
                MemoClaimOut(id="c1", text="Alpha’s Sharpe is 1.36 — solid.",
                             refs=["metric:f1:sharpe"], verified=True, issues=[]),
                MemoClaimOut(id="c2", text="A dubious figure.", refs=[],
                             verified=False, issues=["ungrounded number: 9.9"]),
            ]),
        ],
        facts={sharpe.id: sharpe}, appendix=appendix,
    )


def test_pdf_export_is_a_pdf():
    data = memo_to_pdf(_memo_out())
    assert data[:4] == b"%PDF"
    assert len(data) > 500


def test_docx_export_is_a_docx_zip():
    data = memo_to_docx(_memo_out())
    assert data[:2] == b"PK"  # docx is a zip container
    assert len(data) > 500
