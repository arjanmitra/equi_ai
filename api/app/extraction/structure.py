"""Deterministic table/structure recovery — find the real table inside a messy grid.

Loaders hand this a raw 2-D grid (from csv.reader or an xlsx sheet read with no
header). It locates the header row (skipping comment/title preamble), drops blank
rows, reconciles ragged rows to the table's modal width, de-duplicates/repairs
column names, and returns a clean DataFrame plus human-readable notes describing
what it cleaned. Nothing here is schema-aware — that's the mapping layer's job.

The guarantee that matters: this never raises on a weird grid; worst case it
returns an empty DataFrame with a note, so extraction degrades gracefully
instead of failing the whole file.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

import pandas as pd

_NUM_RE = re.compile(r"^[\s$]*-?[\d,]+(?:\.\d+)?\s*%?$")
_MISSING = {"", "na", "n/a", "nan", "none", "null", "-"}


def _cell(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _is_number(s: str) -> bool:
    return bool(_NUM_RE.match(s))


def _fit(row: list[str], width: int) -> list[str]:
    row = list(row[:width])
    return row + [""] * (width - len(row))


def _clean_header(header: list[str]) -> tuple[list[str], list[str]]:
    """Name empty headers, de-duplicate repeats. Returns (names, repaired_labels)."""
    out: list[str] = []
    seen: dict[str, int] = {}
    repaired: list[str] = []
    for i, h in enumerate(header):
        name = h or f"column_{i + 1}"
        if not h:
            repaired.append(name)
        if name in seen:
            seen[name] += 1
            repaired.append(name)
            name = f"{name}.{seen[name]}"
        else:
            seen[name] = 0
        out.append(name)
    return out, repaired


def _find_header(rows: list[list[str]], modal: int) -> int:
    """Index of the first row that looks like a header: near-modal width, mostly
    filled, and mostly non-numeric (labels, not data)."""
    for i, r in enumerate(rows):
        filled = [c for c in r[:modal] if c != ""]
        if len(filled) < max(2, modal - 1):
            continue  # too narrow / mostly empty -> preamble or junk
        numeric = sum(1 for c in filled if _is_number(c))
        if numeric / len(filled) > 0.4:
            continue  # looks like data, not a header
        return i
    return 0  # headerless fallback: treat the first row as the header


def recover_grid(grid: list[list[Any]]) -> tuple[pd.DataFrame, list[str]]:
    notes: list[str] = []
    rows = [[_cell(c) for c in r] for r in grid]

    blanks = sum(1 for r in rows if not any(c for c in r))
    rows = [r for r in rows if any(c for c in r)]
    if blanks:
        notes.append(f"dropped {blanks} blank row(s)")
    if not rows:
        return pd.DataFrame(), notes + ["no non-empty rows found"]

    widths = Counter(len(r) for r in rows if len(r) >= 2)
    modal = widths.most_common(1)[0][0] if widths else len(rows[0])

    hdr = _find_header(rows, modal)
    if hdr > 0:
        notes.append(f"skipped {hdr} preamble row(s) before the header")

    header, repaired = _clean_header(_fit(rows[hdr], modal))
    if repaired:
        notes.append(f"repaired/de-duplicated column name(s): {', '.join(sorted(set(repaired)))}")

    data: list[list[str]] = []
    ragged = 0
    for r in rows[hdr + 1:]:
        if len(r) == modal:
            data.append(r)
            continue
        ragged += 1
        if len(r) > modal:
            trimmed = list(r)
            while len(trimmed) > modal and trimmed[-1] == "":
                trimmed.pop()
            data.append(_fit(trimmed, modal))
        else:
            data.append(_fit(r, modal))
    if ragged:
        notes.append(f"reconciled {ragged} ragged row(s) to {modal} columns")

    df = pd.DataFrame(data, columns=header)

    keep = [c for c in df.columns if (df[c].astype(str).str.strip() != "").any()]
    if len(keep) < len(df.columns):
        notes.append(f"dropped {len(df.columns) - len(keep)} fully-empty column(s)")
        df = df[keep]

    return df, notes
