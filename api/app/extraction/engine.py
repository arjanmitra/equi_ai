"""The extraction orchestrator — the single entry point both apps would call.

    extract(raw, filename, target) -> ExtractionResult

Schema-parameterized: pass a different `target` and the same engine serves a
different product. Option B passes the canonical `Fund`; a document-intelligence
app would pass a flexible record schema. Per-file failures are caught and
reported, never raised, so a batch never dies on one bad file.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.extraction.loaders import route
from app.extraction.loaders.base import TabularContent
from app.extraction.mapping import map_document, map_tabular
from app.schemas.extraction import ExtractionResult, IssueLevel, ValidationReport


def extract(raw: bytes, filename: str, target: type[BaseModel]) -> ExtractionResult:
    try:
        mime, loader = route(raw, filename)
        content = loader.load(raw, filename)
    except Exception as exc:  # noqa: BLE001 - intentional per-file isolation
        report = ValidationReport()
        report.add(IssueLevel.ERROR, f"failed to load file: {exc}")
        return ExtractionResult(
            source_name=filename,
            target_schema=target.__name__,
            strategy="none",
            report=report,
        )

    if isinstance(content, TabularContent):
        result = map_tabular(content, target)
    else:
        result = map_document(content, target)

    result.report.add(IssueLevel.INFO, f"detected mime: {mime}")
    return result
