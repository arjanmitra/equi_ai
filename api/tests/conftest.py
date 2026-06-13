"""Test hygiene: force the deterministic offline paths.

Regardless of what's in the repo `.env`, tests must be hermetic and free:
  - no LLM calls (null the shared client → tabular heuristic / no document path),
  - no live market data (force MARKET_DATA=fixture → synthetic benchmarks/rf).
The live paths are exercised by scripts/evaluate_corpus.py + manual smokes, not
pytest. `settings` is a frozen dataclass, so we override via object.__setattr__.
"""

from __future__ import annotations

import pytest

from app.config import settings
from app.extraction.llm import llm


@pytest.fixture(autouse=True)
def _force_offline(monkeypatch):
    saved_client = llm._client
    saved_mode = settings.market_data_mode
    llm._client = None
    object.__setattr__(settings, "market_data_mode", "fixture")
    yield
    llm._client = saved_client
    object.__setattr__(settings, "market_data_mode", saved_mode)
