"""Document mapping: direct field extraction from prose / images.

Unlike the tabular path, here the model DOES read values (there is no column
grid to map). That makes this the path where numeric-transcription risk lives,
so we (a) force structured output, (b) run the repair loop on validation
failure, and (c) tag provenance back to the document. A verification pass over
the riskiest numeric fields is a natural next step (left as a TODO hook).
"""

from __future__ import annotations

from pydantic import BaseModel, create_model

from app.config import settings
from app.extraction.field_spec import specs_as_text
from app.extraction.llm import llm
from app.extraction.loaders.base import DocumentContent
from app.extraction.repair import extract_with_repair
from app.schemas.extraction import (
    ExtractionResult,
    FieldProvenance,
    IssueLevel,
    ValidationReport,
)

_SYSTEM = """You extract structured records from a financial document.

You are given a target schema and the document content (text and/or page
images). Return every distinct fund/record the document describes, conforming
exactly to the schema.

Hard rules:
- Transcribe numeric values EXACTLY as shown. Do not round, rescale, or infer.
- Express fees and percentages as decimals (2% -> 0.02).
- If a field is not present in the document, leave it null. Never guess.
- If the document describes a single fund, return a list with one record.
"""


def _batch_model(target: type[BaseModel]) -> type[BaseModel]:
    """Wrap the target in a {records: [...]} container for list extraction."""
    return create_model("RecordBatch", records=(list[target], ...))


def map_document(
    content: DocumentContent, target: type[BaseModel]
) -> ExtractionResult:
    report = ValidationReport()

    if not llm.available:
        report.add(
            IssueLevel.ERROR,
            "document extraction requires an LLM, but no ANTHROPIC_API_KEY is set.",
        )
        return ExtractionResult(
            source_name=content.source_name,
            target_schema=target.__name__,
            strategy="document",
            report=report,
        )

    batch = _batch_model(target)
    user = _build_user_text(content, target)

    instance, attempt_log = extract_with_repair(
        model=settings.document_model,
        system=_SYSTEM,
        user_text=user,
        schema=batch,
        images=content.page_images,
    )
    for line in attempt_log:
        report.add(IssueLevel.FLAG, f"repair: {line}")

    records: list[dict] = []
    provenance: list[FieldProvenance] = []

    if instance is None:
        report.add(IssueLevel.ERROR, "extraction failed after repair attempts.")
        report.records_failed += 1
    else:
        extracted = getattr(instance, "records", [])
        report.total_rows = len(extracted)
        for index, rec in enumerate(extracted):
            records.append(rec.model_dump(mode="json"))
            report.records_ok += 1
            for field_name, value in rec.model_dump(mode="json").items():
                if value is None:
                    continue
                provenance.append(
                    FieldProvenance(
                        record_index=index,
                        target_field=field_name,
                        raw_value=value,
                        normalized_value=value,
                        source=f"document: {content.source_name}",
                        confidence=None,
                    )
                )

    return ExtractionResult(
        source_name=content.source_name,
        target_schema=target.__name__,
        strategy="document",
        records=records,
        provenance=provenance,
        report=report,
    )


def _build_user_text(content: DocumentContent, target: type[BaseModel]) -> str:
    parts = [f"Target schema fields:\n{specs_as_text(target)}\n"]
    if content.text:
        # Cap text to keep the prompt bounded; page images carry the rest.
        snippet = content.text[:20_000]
        parts.append(f"Document text:\n{snippet}")
    if content.page_images:
        parts.append(
            f"\n({len(content.page_images)} page image(s) attached — read values "
            f"from them where text is missing.)"
        )
    return "\n".join(parts)
