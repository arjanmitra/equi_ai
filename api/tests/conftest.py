"""Test hygiene: force the deterministic offline paths.

Once an ANTHROPIC_API_KEY is present (e.g. in the repo .env), the engine would
otherwise call the LLM for column mapping and document extraction. Tests must be
hermetic and free, so we null out the shared LLM client for every test. The
offline tabular path (heuristic mapping) is what the suite asserts against; the
live document path is exercised by scripts/evaluate_corpus.py, not pytest.
"""

from __future__ import annotations

import pytest

from app.extraction.llm import llm


@pytest.fixture(autouse=True)
def _force_offline_llm():
    saved = llm._client
    llm._client = None
    yield
    llm._client = saved
