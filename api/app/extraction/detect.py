"""Detect file type from bytes, never trusting the extension blindly.

`filetype` recognizes binary containers (xlsx is a zip, pdf has a magic header).
Text formats (csv/tsv/html) have no reliable magic, so we sniff content and fall
back to the extension as a tiebreaker.
"""

from __future__ import annotations

import os

import filetype

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF_MIME = "application/pdf"
HTML_MIME = "text/html"
CSV_MIME = "text/csv"


def detect_mime(raw: bytes, filename: str) -> str:
    """Return a best-effort mime type string."""
    kind = filetype.guess(raw)
    if kind is not None:
        # filetype reports xlsx/xls as a zip on some versions; disambiguate.
        if kind.mime in (XLSX_MIME, "application/zip") and _looks_like_xlsx(raw):
            return XLSX_MIME
        if kind.mime == PDF_MIME:
            return PDF_MIME

    ext = os.path.splitext(filename)[1].lower()
    if ext in {".xlsx", ".xls", ".xlsm"}:
        return XLSX_MIME
    if ext == ".pdf":
        return PDF_MIME

    # Text-ish: sniff a decoded sample.
    head = raw[:4096].lstrip()
    if head[:1] in (b"<",) or b"<html" in head[:512].lower() or b"<table" in head.lower():
        return HTML_MIME
    if ext in {".html", ".htm"}:
        return HTML_MIME

    # Default: treat as delimited text (csv/tsv). The CSV loader sniffs the
    # actual delimiter.
    return CSV_MIME


def _looks_like_xlsx(raw: bytes) -> bool:
    # xlsx zips contain this entry path near the top of the archive.
    return raw[:2] == b"PK" and b"xl/" in raw[:4096]
