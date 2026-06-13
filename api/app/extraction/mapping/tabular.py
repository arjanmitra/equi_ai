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

    # Surface what structure recovery did to the raw grid (preamble skipped,
    # ragged rows reconciled, columns de-duplicated) so it's visible + auditable.
    for note in content.extra.get("structure_notes", []):
        report.add(IssueLevel.INFO, f"structure: {note}")

    valid_mappings = [m for m in plan.mappings if m.source_column in df.columns]
    for m in plan.mappings:
        if m.source_column not in df.columns:
            report.add(
                IssueLevel.INFO,
                f"plan referenced unknown column '{m.source_column}' — skipped.",
                field=m.target_field,
            )

    # Columns the plan didn't map become the source-attributed "attribute bag":
    # captured verbatim per row as kind="extra" provenance so they're displayed
    # and citable, but they never reach a Fund field and so never feed
    # metrics/constraints. This preserves the trust wall while stopping silent
    # data loss of fund-describing stats we don't have a canonical slot for.
    mapped_cols = {m.source_column for m in valid_mappings}
    extra_cols = [c for c in df.columns if c not in mapped_cols]
    if extra_cols:
        report.add(
            IssueLevel.INFO,
            "captured "
            f"{len(extra_cols)} unmapped column(s) as reported attributes: "
            f"{', '.join(map(str, extra_cols))}",
        )

    records: list[dict] = []
    provenance: list[FieldProvenance] = []

    for index, (_, row) in enumerate(df.iterrows()):
        record_dict, row_prov = _build_row(row, valid_mappings, index, report)
        row_prov.extend(_extra_attributes(row, extra_cols, index))
        instance, error = coerce_record(record_dict, target)
        if instance is None:
            report.records_failed += 1
            report.add(
                IssueLevel.ERROR,
                f"row dropped: {summarize_errors(error)}",
                record_index=index,  # source-row index (this row isn't in records)
            )
            continue

        # Provenance and per-record flags must index into the *compacted* records
        # list, not the source df, because dropped rows make those diverge.
        pos = len(records)
        for p in row_prov:
            p.record_index = pos
        record_sanity_flags(instance, pos, report)
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


def _extra_attributes(
    row: pd.Series, extra_cols: list[str], index: int
) -> list[FieldProvenance]:
    """Capture unmapped columns verbatim as kind='extra' provenance.

    No transform is applied and the value never lands in a record dict — these
    are untrusted, as-reported attributes, attributed to their source column.
    Empty cells are skipped so the bag stays meaningful.
    """
    out: list[FieldProvenance] = []
    for col in extra_cols:
        raw = row[col]
        if pd.isna(raw) or str(raw).strip() == "":
            continue
        value = str(raw).strip()
        out.append(
            FieldProvenance(
                record_index=index,
                target_field=str(col),
                raw_value=value,
                normalized_value=value,  # verbatim; no coercion
                source=f"column: {col}",
                transform=None,
                confidence=None,
                kind="extra",
            )
        )
    return out


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
