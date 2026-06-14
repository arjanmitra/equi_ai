# Kit 2 — Format gallery (input breadth) · 7 funds

The **same ~7 funds rendered in different file formats** — the point is that the
extraction engine swallows any of them. There are **no returns files here**, so
the risk metrics will show as "pending / n/a" (use Kit 1 or 3 for metrics).

## What to upload — **one file at a time**

Because every file contains the *same* funds, uploading several at once would
create duplicate funds. For each file: click **New analysis**, put it under
**Fund universe** in Step 1 (leave returns empty), confirm the mapping in Step 2,
and look at the extracted table + provenance. Then start another analysis for the
next file.

| Universe file | Format it demonstrates |
|---|---|
| `clean.csv` | A tidy comma CSV |
| `messy.csv` | A messy CSV (synonym headers, `bps` fees, `$1.2B` AUM, varied dates, missing values, a junk column) |
| `managers.xlsx` | A multi-sheet Excel workbook |
| `email.html` | An HTML email with the data in a `<table>` |
| `factsheet-alpha.pdf` | A **PDF factsheet** — single fund, prose + key-terms list (the LLM **document** path, not the tabular one) |
| `factsheet-beacon.pdf` | A second PDF factsheet |

> The two PDFs need an `ANTHROPIC_API_KEY` (document-reading path). The
> CSV/XLSX/HTML files work with or without a key.

A nice contrast for a reviewer: run `messy.csv` (tabular path → a mapping plan,
code converts the values) and then `factsheet-alpha.pdf` (document path → the
model reads the values directly). Same canonical output, two routes.
