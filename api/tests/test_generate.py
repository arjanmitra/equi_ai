"""Memo generation loop — reject-and-regenerate + flag-and-show.

The LLM is stubbed (no network): we queue drafts and assert the loop verifies,
regenerates on ungrounded output, and flags survivors after the cap.
"""

from __future__ import annotations

import pytest

from app.memo.generate import generate_memo
from app.schemas.catalog import Catalog, Fact
from app.schemas.memo import Claim, MemoDraft, MemoSection


@pytest.fixture
def catalog():
    facts = [
        Fact(id="metric:f1:sharpe", kind="metric", name="sharpe", label="Sharpe",
             value=1.36, display="1.36", fund_id="f1"),
    ]
    return Catalog(run_id="r", mandate=[], funds=[], index={f.id: f for f in facts})


def _draft(text: str, refs: list[str]) -> dict:
    return MemoDraft(
        sections=[MemoSection(kind="summary", title="Summary",
                              claims=[Claim(text=text, refs=refs)])]
    ).model_dump()


def _stub_llm(monkeypatch, drafts: list[dict]):
    from app.extraction.llm import llm

    queue = list(drafts)

    def fake_structured(**_kwargs):
        return queue.pop(0)

    monkeypatch.setattr(llm, "structured", fake_structured)
    return queue


def test_returns_immediately_when_grounded(monkeypatch, catalog):
    _stub_llm(monkeypatch, [_draft("It posts a Sharpe of 1.36.", ["metric:f1:sharpe"])])
    memo, log = generate_memo(catalog)
    assert memo.all_verified is True
    assert "all 1 claims grounded" in log[-1]


def test_regenerates_then_succeeds(monkeypatch, catalog):
    queue = _stub_llm(monkeypatch, [
        _draft("A Sharpe of 9.99.", ["metric:f1:sharpe"]),   # hallucinated
        _draft("A Sharpe of 1.36.", ["metric:f1:sharpe"]),   # corrected
    ])
    memo, log = generate_memo(catalog)
    assert memo.all_verified is True
    assert queue == []  # both drafts consumed -> it regenerated once
    assert any("ungrounded" in line for line in log)


def test_flags_after_cap(monkeypatch, catalog):
    # Always hallucinated -> after the cap, returned flagged (not dropped).
    _stub_llm(monkeypatch, [_draft("A Sharpe of 9.99.", ["metric:f1:sharpe"])] * 5)
    memo, log = generate_memo(catalog, max_attempts=1)
    assert memo.all_verified is False
    assert len(memo.unverified) == 1
    assert "max attempts reached" in log[-1]
