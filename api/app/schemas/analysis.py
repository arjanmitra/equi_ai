"""Analysis = one end-to-end journey (upload → mandate → run → memo).

This is the row in the Analyses table; its lifecycle pointers fill in as the
wizard progresses. Cancelling the wizard deletes the analysis (and its upload).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AnalysisCreate(BaseModel):
    upload_id: str
    label: str | None = None


class AnalysisUpdate(BaseModel):
    label: str | None = None
    mandate_id: str | None = None
    run_id: str | None = None
    memo_id: str | None = None


class AnalysisOut(BaseModel):
    id: str
    created_at: datetime
    label: str | None
    upload_id: str
    mandate_id: str | None
    run_id: str | None
    memo_id: str | None
    universe_files: list[str]
    returns_files: list[str]
    has_memo: bool
