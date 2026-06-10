"""Tabular mapping: the headline reliability pattern.

The LLM (or the offline heuristic) produces a *mapping plan* — column -> field +
transform — from headers and a few sample rows only. We then apply that plan to
every row deterministically. The model never transcribes a value, so numbers
stay exact and the whole table costs one cheap LLM call regardless of length.
"""

from __future__ import annotations

import json

import pandas as pd
from pydantic import BaseModel

from app.config import settings
from app.extraction.field_spec import specs_as_text
from app.extraction.llm import llm
from app.extraction.loaders.base import TabularContent
from app.extraction.mapping.heuristic import heuristic_plan
from app.extraction.transforms import apply_transform
from app.extraction.validate import coerce_record, record_sanity_flags, summarize_errors
from app.schemas.extraction import (
    ExtractionResult,
    FieldProvenance,
    IssueLevel,
    ValidationReport,
)
from app.schemas.mapping import ColumnMap, MappingPlan

_SYSTEM = """You map messy tabular financial data onto a fixed target schema.

You are given the target fields and a few SAMPLE rows of a source table. Decide,
for each target field you can satisfy, which source column feeds it and which
transform normalizes it.

Hard rules:
- Do NOT transcribe, compute, or invent any data values. Map columns only.
- Use a source column at most once.
- Choose a transform from the allowed enum based on how the VALUES are written:
  `percent_to_decimal` for '2%' style, `bps_to_decimal` for basis points
  ('150 bps'), `strip_currency` for money ('$1.2B'), `parse_date` for dates,
  `parse_int` for whole-number day/month counts, and `none` when the value is
  already in the target form (e.g. a fee given as the decimal 0.02).
- Leave a target field unmapped if no column plausibly matches.
- List every source column you did not map in `unmapped_columns`.
"""


def _column_samples(content: TabularContent) -> dict[str, list[str]]:
    """Column -> a few non-empty sample values, for value-aware transform guess."""
    rows = content.sample_rows(settings.mapping_sample_rows)
    return {
        col: [str(r[col]) for r in rows if r.get(col) not in (None, "")]
        for col in content.columns
    }


def _get_plan(content: TabularContent, target: type[BaseModel]) -> tuple[MappingPlan, str]:
    """Return (plan, source_label). Falls back to the heuristic when offline."""
    samples = _column_samples(content)
    if not llm.available:
        return heuristic_plan(content.columns, target, samples), "heuristic"

    user = (
        f"Target schema fields:\n{specs_as_text(target)}\n\n"
        f"Source columns: {content.columns}\n\n"
        f"Sample rows (raw strings):\n"
        f"{json.dumps(content.sample_rows(settings.mapping_sample_rows), indent=2)}"
    )
    try:
        raw = llm.structured(
            model=settings.mapping_model,
            system=_SYSTEM,
            user_text=user,
            schema=MappingPlan,
        )
        return MappingPlan.model_validate(raw), "llm"
    except Exception:
        # Any LLM/validation failure -> degrade gracefully to the heuristic.
        return heuristic_plan(content.columns, target, samples), "heuristic-fallback"


def map_tabular(
    content: TabularContent, target: type[BaseModel]
) -> ExtractionResult:
    plan, plan_source = _get_plan(content, target)
    df = content.df
    report = ValidationReport(total_rows=len(df), unmapped_columns=plan.unmapped_columns)

    valid_mappings = [m for m in plan.mappings if m.source_column in df.columns]
    for m in plan.mappings:
        if m.source_column not in df.columns:
            report.add(
                IssueLevel.INFO,
                f"plan referenced unknown column '{m.source_column}' — skipped.",
                field=m.target_field,
            )

    records: list[dict] = []
    provenance: list[FieldProvenance] = []

    for index, (_, row) in enumerate(df.iterrows()):
        record_dict, row_prov = _build_row(row, valid_mappings, index, report)
        instance, error = coerce_record(record_dict, target)
        if instance is None:
            report.records_failed += 1
            report.add(
                IssueLevel.ERROR,
                f"row dropped: {summarize_errors(error)}",
                record_index=index,
            )
            continue

        record_sanity_flags(instance, index, report)
        records.append(instance.model_dump(mode="json"))
        provenance.extend(row_prov)
        report.records_ok += 1

    report.add(IssueLevel.INFO, f"mapping plan produced by: {plan_source}")
    return ExtractionResult(
        source_name=content.source_name,
        target_schema=target.__name__,
        strategy="tabular",
        records=records,
        provenance=provenance,
        report=report,
    )


def _build_row(
    row: pd.Series,
    mappings: list[ColumnMap],
    index: int,
    report: ValidationReport,
) -> tuple[dict, list[FieldProvenance]]:
    record_dict: dict = {}
    row_prov: list[FieldProvenance] = []

    for m in mappings:
        raw_value = row[m.source_column]
        try:
            normalized = apply_transform(raw_value, m.transform)
        except (ValueError, TypeError) as exc:
            report.add(
                IssueLevel.FLAG,
                f"transform '{m.transform.value}' failed on "
                f"'{m.source_column}'={raw_value!r}: {exc}",
                record_index=index,
                field=m.target_field,
            )
            normalized = None

        record_dict[m.target_field] = normalized
        row_prov.append(
            FieldProvenance(
                record_index=index,
                target_field=m.target_field,
                raw_value=None if pd.isna(raw_value) else str(raw_value),
                normalized_value=normalized,
                source=f"column: {m.source_column}",
                transform=m.transform.value,
                confidence=m.confidence,
            )
        )

    return record_dict, row_prov
