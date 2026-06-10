"""CSV/TSV loader with encoding + delimiter sniffing."""

from __future__ import annotations

import csv
import io

import pandas as pd
from charset_normalizer import from_bytes

from app.extraction.detect import CSV_MIME
from app.extraction.loaders.base import TabularContent


class CsvLoader:
    def can_load(self, mime: str, filename: str) -> bool:
        return mime == CSV_MIME or filename.lower().endswith((".csv", ".tsv", ".txt"))

    def load(self, raw: bytes, filename: str) -> TabularContent:
        text = self._decode(raw)
        sep = self._sniff_delimiter(text)
        df = pd.read_csv(
            io.StringIO(text),
            sep=sep,
            dtype=str,  # keep raw strings; transforms coerce later
            keep_default_na=False,
            skip_blank_lines=True,
            engine="python",
        )
        df = df.dropna(axis=1, how="all")
        df.columns = [str(c).strip() for c in df.columns]
        return TabularContent(source_name=filename, df=df)

    @staticmethod
    def _decode(raw: bytes) -> str:
        best = from_bytes(raw).best()
        if best is not None:
            return str(best)
        return raw.decode("utf-8", errors="replace")

    @staticmethod
    def _sniff_delimiter(text: str) -> str:
        sample = "\n".join(text.splitlines()[:20])
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            return dialect.delimiter
        except csv.Error:
            # Heuristic fallback: pick the most common candidate in the header.
            header = text.splitlines()[0] if text.splitlines() else ""
            counts = {d: header.count(d) for d in [",", ";", "\t", "|"]}
            best = max(counts, key=counts.get)
            return best if counts[best] > 0 else ","
