"""PDF loader with a tiered strategy.

1. Native text first: PyMuPDF4LLM turns a text PDF into clean markdown. Cheap,
   CPU-only, exact text — ideal for digitally-generated factsheets.
2. Escalate to vision only when the native parse looks thin (scanned/image
   PDF): rasterize pages to PNG and let the document mapper read them with a
   vision model. This is the "route by document difficulty to control cost"
   decision worth naming in the walkthrough.
"""

from __future__ import annotations

import base64

from app.extraction.loaders.base import DocumentContent

# Below this much extracted text we assume the PDF is scanned/image-based.
_THIN_TEXT_CHARS = 200


class PdfLoader:
    def can_load(self, mime: str, filename: str) -> bool:
        return mime == "application/pdf" or filename.lower().endswith(".pdf")

    def load(self, raw: bytes, filename: str) -> DocumentContent:
        text = self._native_markdown(raw)
        if text and len(text.strip()) >= _THIN_TEXT_CHARS:
            return DocumentContent(
                source_name=filename, text=text, extra={"path": "native"}
            )

        images = self._rasterize(raw)
        return DocumentContent(
            source_name=filename,
            text=text or None,
            page_images=images,
            extra={"path": "vision", "reason": "thin native text"},
        )

    @staticmethod
    def _native_markdown(raw: bytes) -> str:
        import tempfile

        try:
            import pymupdf4llm

            with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
                tmp.write(raw)
                tmp.flush()
                return pymupdf4llm.to_markdown(tmp.name)
        except Exception:
            return ""

    @staticmethod
    def _rasterize(raw: bytes, max_pages: int = 8) -> list[str]:
        try:
            import fitz  # pymupdf
        except ImportError:
            return []

        images: list[str] = []
        doc = fitz.open(stream=raw, filetype="pdf")
        for page in doc[:max_pages]:
            pix = page.get_pixmap(dpi=150)
            images.append(base64.b64encode(pix.tobytes("png")).decode())
        doc.close()
        return images
