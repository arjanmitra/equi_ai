"""XLSX loader. Reads the first sheet by default.

Multi-sheet workbooks are common (one sheet per fund, or returns on a second
sheet). For the scaffold we take the first non-empty sheet and record the others
in `extra` so a later pass can decide what to do — a deliberate, documented
scope cut rather than silent data loss.
"""

from __future__ import annotations

import io

import pandas as pd

from app.extraction.detect import XLSX_MIME
from app.extraction.loaders.base import TabularContent


class XlsxLoader:
    def can_load(self, mime: str, filename: str) -> bool:
        return mime == XLSX_MIME or filename.lower().endswith(
            (".xlsx", ".xls", ".xlsm")
        )

    def load(self, raw: bytes, filename: str) -> TabularContent:
        book = pd.read_excel(io.BytesIO(raw), sheet_name=None, dtype=str)
        sheet_names = list(book.keys())
        # First sheet that actually has rows.
        chosen, df = next(
            ((name, d) for name, d in book.items() if not d.dropna(how="all").empty),
            (sheet_names[0], book[sheet_names[0]]),
        )
        df = df.dropna(axis=1, how="all").fillna("")
        df.columns = [str(c).strip() for c in df.columns]
        return TabularContent(
            source_name=f"{filename}#{chosen}",
            df=df,
            extra={"sheet": chosen, "other_sheets": [s for s in sheet_names if s != chosen]},
        )
