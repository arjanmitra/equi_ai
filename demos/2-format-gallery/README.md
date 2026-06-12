# Kit 2 — Format gallery (input breadth) · 7 funds

These are the **same ~7 funds rendered in different file formats**. The point is
to show the extraction engine swallows any of them. There are **no returns files
here**, so after extracting, the risk metrics will show as "pending / n/a" —
that's expected. (To see metrics, use Kit 1 or Kit 3.)

## Upload these **one at a time** (not all together)

Because they all contain the *same* funds, uploading several at once would create
duplicate fund rows. Upload one, look at the extracted table + provenance, then
start a "New analysis" and try the next.

| File | Format it demonstrates |
|---|---|
| `clean.csv` | A tidy comma CSV |
| `messy.csv` | A messy CSV (synonym headers, `bps` fees, `$1.2B` AUM, varied dates, missing values, a junk column) |
| `managers.xlsx` | A multi-sheet Excel workbook |
| `email.html` | An HTML email with the data in a `<table>` |
| `factsheet-alpha.pdf` | A **PDF factsheet** — single fund, prose + a key-terms list (the LLM **document** path, not the tabular one) |
| `factsheet-beacon.pdf` | A second PDF factsheet |

> The two PDFs need an `ANTHROPIC_API_KEY` (they go through the document-reading
> path). The CSV/XLSX/HTML files work with or without a key.

A nice contrast to show a reviewer: upload `messy.csv` (tabular path → a mapping
plan, code converts the values) and then `factsheet-alpha.pdf` (document path →
the model reads the values directly). Same canonical output, two routes.
