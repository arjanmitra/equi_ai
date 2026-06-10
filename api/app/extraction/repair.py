"""Generic repair loop: re-prompt the model with the exact validation error.

Used by the document path (free-form LLM extraction is where coercion most often
fails). The tabular path rarely needs it because values are produced by
deterministic transforms — but the same primitive is available if a mapping
plan yields a systematically uncoercible column.
"""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from app.config import settings
from app.extraction.llm import llm
from app.extraction.validate import summarize_errors


def extract_with_repair(
    *,
    model: str,
    system: str,
    user_text: str,
    schema: type[BaseModel],
    images: list[str] | None = None,
    max_attempts: int | None = None,
) -> tuple[BaseModel | None, list[str]]:
    """Call the LLM for `schema`, retrying with error feedback on failure.

    Returns (instance | None, attempt_log). The log records each failure reason,
    which is useful to surface in the validation report.
    """
    attempts = max_attempts or settings.max_repair_attempts
    log: list[str] = []
    text = user_text

    for attempt in range(attempts + 1):
        raw = llm.structured(
            model=model,
            system=system,
            user_text=text,
            schema=schema,
            images=images,
        )
        try:
            return schema.model_validate(raw), log
        except ValidationError as exc:
            reason = summarize_errors(exc)
            log.append(f"attempt {attempt + 1}: {reason}")
            if attempt == attempts:
                break
            text = (
                f"{user_text}\n\nYour previous output failed validation with:\n"
                f"{reason}\n\nReturn corrected output that satisfies the schema."
            )

    return None, log
