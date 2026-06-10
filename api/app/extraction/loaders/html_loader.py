"""HTML loader.

Financial HTML (emails, factsheet exports) usually carries the data in a
<table>. So we try to lift tables first and treat the file as tabular; only if
there is no usable table do we fall back to a document (prose) path.
"""

from __future__ import annotations

import io

import pandas as pd

from app.extraction.detect import HTML_MIME
from app.extraction.loaders.base import DocumentContent, LoadedContent, TabularContent


class HtmlLoader:
    def can_load(self, mime: str, filename: str) -> bool:
        return mime == HTML_MIME or filename.lower().endswith((".html", ".htm"))

    def load(self, raw: bytes, filename: str) -> LoadedContent:
        text = raw.decode("utf-8", errors="replace")

        tables = self._read_tables(text)
        if tables:
            df = max(tables, key=lambda d: d.shape[0] * d.shape[1])
            df = df.dropna(axis=1, how="all").fillna("")
            df.columns = [str(c).strip() for c in df.columns]
            return TabularContent(source_name=filename, df=df)

        return DocumentContent(source_name=filename, text=self._extract_text(text))

    @staticmethod
    def _read_tables(text: str) -> list[pd.DataFrame]:
        try:
            return pd.read_html(io.StringIO(text))
        except (ValueError, ImportError):
            return []

    @staticmethod
    def _extract_text(text: str) -> str:
        try:
            import trafilatura

            extracted = trafilatura.extract(text)
            if extracted:
                return extracted
        except Exception:
            pass
        # Fallback: strip tags with BeautifulSoup.
        from bs4 import BeautifulSoup

        return BeautifulSoup(text, "lxml").get_text(separator="\n", strip=True)
