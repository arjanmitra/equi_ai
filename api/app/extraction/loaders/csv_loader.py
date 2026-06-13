"""CSV/TSV loader with encoding + delimiter sniffing."""

from __future__ import annotations

import csv
import io

from charset_normalizer import from_bytes

from app.extraction.detect import CSV_MIME
from app.extraction.loaders.base import TabularContent
from app.extraction.structure import recover_grid


class CsvLoader:
    def can_load(self, mime: str, filename: str) -> bool:
        return mime == CSV_MIME or filename.lower().endswith((".csv", ".tsv", ".txt"))

    def load(self, raw: bytes, filename: str) -> TabularContent:
        text = self._decode(raw)
        sep = self._sniff_delimiter(text)
        # csv.reader handles quoting; recover_grid finds the real table within
        # (preamble, blank/ragged rows, duplicate columns) instead of assuming a
        # clean grid that read_csv would choke on.
        grid = list(csv.reader(io.StringIO(text), delimiter=sep))
        df, notes = recover_grid(grid)
        return TabularContent(
            source_name=filename, df=df, extra={"structure_notes": notes}
        )

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
