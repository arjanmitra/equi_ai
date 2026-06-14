# Demo data — what to upload, and when

Ready-to-use sample bundles for driving the app end to end. Each numbered folder
is a **self-contained kit**. Open the folder, read its short `README`, and upload
the files it lists.

## The one rule to remember

> **Returns attach to funds by matching the fund _name_.** A returns file only
> works with a universe file that has the same fund names. Each kit uses
> **different fund names**, so never mix files across kits.

The **universe** file is where funds come from. **Returns** files just add monthly
history to funds that already exist.

## How to upload (the New Analysis wizard)

Everything happens in one flow. Click **New analysis** (top-right), then:

1. **Step 1 — Upload data.** Choose the kit's **universe** file under *Fund
   universe*, and its **returns** file(s) under *Monthly returns (optional)*.
   Click **Continue**.
2. **Step 2 — Review mapping.** Confirm (or edit) how each source column maps to
   the canonical schema; the preview updates live. Click **Looks good — continue**.
3. **Step 3 — Choose a mandate.** Pick an existing one, or **Create new mandate**
   (each kit suggests one). Click **Continue**.
4. **Step 4 — Review evaluation.** See the ranked shortlist. Click **Generate IC
   Memo** — you land on the analysis, the memo generates, and citation chips trace
   each claim back to a metric or source column.

> Returns are optional. Without them, the risk metrics (volatility, drawdown,
> Sharpe) simply show as "pending / n/a" and those constraints report as not
> evaluated. Steps still complete.

## The kits

| Folder | Universe file(s) | Returns file(s) | What it shows |
|---|---|---|---|
| **`1-quickstart/`** | `universe.csv` (5 funds) | all 3 `returns-*.csv` | **Start here.** The full lifecycle, small enough to read every number, with a live risk-constraint exclusion and a grounded memo. |
| **`2-format-gallery/`** | each file, **one at a time** | _(none)_ | Input-format breadth: clean CSV, messy CSV, XLSX, HTML email, and two PDF factsheets (the LLM document path). |
| **`3-scale-and-edge-cases/`** | `universe.csv` (120 funds) | `returns.csv` + `returns-messy.csv` | Scale + edge cases: extreme drawdown, zero-volatility, low-confidence flags, an unmatched fund, duplicate names. |
| **`4-robust-extraction/`** | one of the `universe-*` files (or `managers-messy.xlsx`) | `returns.csv` | Robustness: structure recovery (preamble, ragged rows, duplicate columns) and the attribute bag (unmapped columns kept as untrusted, citable attributes). |

## Notes

- **Uploading multiple *universe* files at once creates duplicate funds** — upload
  one universe per analysis. Multiple *returns* files together is always fine.
- The **PDF (document) path** and **memo generation** need an `ANTHROPIC_API_KEY`
  (in `.env` at the repo root or `api/`). Everything else works without one.
