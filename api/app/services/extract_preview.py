"""Build a no-persistence preview for the mapping-review step.

Routes + loads a file exactly as the committer will, computes (or accepts an
override of) the column→field plan, applies it to produce a faithful preview,
and returns it — writing nothing to the database. The tabular path costs the
same single mapping call as a normal extract; re-previews with an override (the
live-preview-on-edit case) make no LLM call at all. The document path is not
previewed here — it has no columns to review and its values are read once, on
commit, to avoid paying the expensive document call twice.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.extraction.loaders import route
from app.extraction.loaders.base import TabularContent
from app.extraction.mapping.tabular import column_samples, map_tabular, resolve_plan
from app.schemas.extract_plan import PlanFile
from app.schemas.extraction import FieldIssue, IssueLevel
from app.schemas.mapping import MappingPlan

PREVIEW_ROWS = 5


def preview_file(
    raw: bytes,
    filename: str,
    target: type[BaseModel],
    override: MappingPlan | None = None,
) -> PlanFile:
    try:
        _mime, loader = route(raw, filename)
        content = loader.load(raw, filename)
    except Exception as exc:  # noqa: BLE001 - mirror the engine's per-file isolation
        return PlanFile(
            filename=filename,
            strategy="none",
            issues=[FieldIssue(level=IssueLevel.ERROR, message=f"failed to load file: {exc}")],
        )

    if not isinstance(content, TabularContent):
        # Document path: nothing to map. Values are extracted on commit.
        return PlanFile(
            filename=filename,
            strategy="document",
            issues=[
                FieldIssue(
                    level=IssueLevel.INFO,
                    message="document path — values are read on commit, no column mapping to review.",
                )
            ],
        )

    plan_obj, _source = resolve_plan(content, target, override)
    result = map_tabular(content, target, plan=plan_obj)
    return PlanFile(
        filename=filename,
        strategy="tabular",
        plan=plan_obj,
        columns=content.columns,
        column_samples=column_samples(content),
        preview=result.records[:PREVIEW_ROWS],
        structure_notes=list(content.extra.get("structure_notes", [])),
        issues=result.report.issues,
    )
