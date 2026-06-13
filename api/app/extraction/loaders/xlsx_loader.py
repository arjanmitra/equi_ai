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
from app.extraction.structure import recover_grid


class XlsxLoader:
    def can_load(self, mime: str, filename: str) -> bool:
        return mime == XLSX_MIME or filename.lower().endswith(
            (".xlsx", ".xls", ".xlsm")
        )

    def load(self, raw: bytes, filename: str) -> TabularContent:
        # header=None: read every sheet as a raw grid so recover_grid (not
        # pandas' fixed row-0 assumption) decides where the header lives.
        book = pd.read_excel(io.BytesIO(raw), sheet_name=None, dtype=str, header=None)
        sheet_names = list(book.keys())
        # First sheet that actually has rows.
        chosen, raw_df = next(
            ((name, d) for name, d in book.items() if not d.dropna(how="all").empty),
            (sheet_names[0], book[sheet_names[0]]),
        )
        grid = raw_df.where(pd.notna(raw_df), None).values.tolist()
        df, notes = recover_grid(grid)
        return TabularContent(
            source_name=f"{filename}#{chosen}",
            df=df,
            extra={
                "sheet": chosen,
                "other_sheets": [s for s in sheet_names if s != chosen],
                "structure_notes": notes,
            },
        )
