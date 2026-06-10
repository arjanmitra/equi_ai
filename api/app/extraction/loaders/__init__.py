"""Format-specific loaders. Each turns raw bytes into a normalized intermediate
(TabularContent or DocumentContent). They are intentionally 'dumb': no schema
awareness, no LLM — that all lives in the shared mapping layer.
"""

from __future__ import annotations

from app.extraction.detect import (
    HTML_MIME,
    PDF_MIME,
    XLSX_MIME,
    detect_mime,
)
from app.extraction.loaders.base import (
    DocumentContent,
    LoadedContent,
    Loader,
    TabularContent,
)
from app.extraction.loaders.csv_loader import CsvLoader
from app.extraction.loaders.html_loader import HtmlLoader
from app.extraction.loaders.pdf_loader import PdfLoader
from app.extraction.loaders.xlsx_loader import XlsxLoader

# Order matters only for readability; routing is explicit by mime below.
_LOADERS: list[Loader] = [CsvLoader(), XlsxLoader(), HtmlLoader(), PdfLoader()]


def route(raw: bytes, filename: str) -> tuple[str, Loader]:
    """Detect the mime and return (mime, the loader that handles it)."""
    mime = detect_mime(raw, filename)
    for loader in _LOADERS:
        if loader.can_load(mime, filename):
            return mime, loader
    # Fall back to CSV — the most permissive text loader.
    return mime, CsvLoader()


__all__ = [
    "DocumentContent",
    "TabularContent",
    "LoadedContent",
    "Loader",
    "route",
    "detect_mime",
    "HTML_MIME",
    "PDF_MIME",
    "XLSX_MIME",
]
