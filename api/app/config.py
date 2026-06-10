"""Runtime configuration.

Everything reads from the environment so the same code runs offline (no key)
in tests/CI and online in a real demo. The extraction core is deliberately
usable without a key: tabular mapping degrades to a heuristic matcher.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY") or None

    # Model routing by task difficulty (a deliberate "route by difficulty"
    # decision worth calling out in the walkthrough).
    mapping_model: str = os.getenv("MAPPING_MODEL", "claude-haiku-4-5-20251001")
    document_model: str = os.getenv("DOCUMENT_MODEL", "claude-sonnet-4-6")
    memo_model: str = os.getenv("MEMO_MODEL", "claude-opus-4-8")

    # Repair loop: how many times we re-prompt the model with the validation
    # error before giving up on a record.
    max_repair_attempts: int = int(os.getenv("MAX_REPAIR_ATTEMPTS", "2"))

    # How many rows of a table we show the LLM when asking for a mapping plan.
    # The plan is applied deterministically to ALL rows, so this stays small.
    mapping_sample_rows: int = int(os.getenv("MAPPING_SAMPLE_ROWS", "8"))

    @property
    def llm_available(self) -> bool:
        return bool(self.anthropic_api_key)


settings = Settings()
