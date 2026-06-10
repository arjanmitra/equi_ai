"""The normalized intermediate + the Loader protocol.

Downstream mapping only ever sees one of two shapes, regardless of source
format. The full DataFrame stays in code (never sent to the LLM); only a small
preview crosses the model boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

import pandas as pd

from app.config import settings


@dataclass
class TabularContent:
    """A table. The LLM sees `columns` + `sample_rows`; code keeps `df`."""

    source_name: str
    df: pd.DataFrame
    kind: Literal["tabular"] = "tabular"
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def columns(self) -> list[str]:
        return [str(c) for c in self.df.columns]

    @property
    def row_count(self) -> int:
        return int(len(self.df))

    def sample_rows(self, n: int | None = None) -> list[dict]:
        n = n or settings.mapping_sample_rows
        head = self.df.head(n)
        # Stringify so the preview is JSON-serializable and the model sees the
        # raw textual form (e.g. "2%", "$1.2M") it must reason about.
        return [
            {str(k): (None if pd.isna(v) else str(v)) for k, v in row.items()}
            for row in head.to_dict(orient="records")
        ]


@dataclass
class DocumentContent:
    """Unstructured content: markdown text and/or rasterized page images."""

    source_name: str
    text: str | None = None
    page_images: list[str] | None = None  # base64 PNG strings
    kind: Literal["document"] = "document"
    extra: dict[str, Any] = field(default_factory=dict)


LoadedContent = TabularContent | DocumentContent


@runtime_checkable
class Loader(Protocol):
    def can_load(self, mime: str, filename: str) -> bool: ...

    def load(self, raw: bytes, filename: str) -> LoadedContent: ...
