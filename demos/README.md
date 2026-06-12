# Demo data — what to upload, and when

These are ready-to-use sample bundles for driving the app end to end. Each
numbered folder is a **self-contained kit** — open it, read its one-line
`README`, and upload the files it contains.

## The one rule to remember

> **Returns attach to funds by matching the fund _name_.** A returns file only
> works with a universe file that contains the same fund names. The three kits
> use **different fund names**, so never mix files across kits.

Funds come *only* from the universe (the first file you upload). Returns files
just add monthly observations to funds that already exist — so uploading several
returns files together is always safe; uploading several *universe* files would
create duplicate funds.

## The upload order (same for every kit)

1. **Upload the universe file** → click **Extract**.
2. **Attach the returns file(s)** → click **Attach returns**.
3. Click **Compute metrics**.
4. Fill the **Mandate** form → click **Evaluate funds**.
5. Click **Generate IC memo**, then click any citation chip to see it trace back
   to a metric or the original source column. Download as PDF/DOCX.

(Steps 2–3 are optional — without returns, the risk metrics simply show as
"pending / n/a". Steps 1, 4, 5 still work.)

## The kits

| Folder | Funds | Returns? | What it shows |
|---|---|---|---|
| `1-quickstart/` | 5 | ✅ | **The full lifecycle**, small enough to read — incl. a live risk-constraint exclusion and a clean, grounded memo. **Start here.** |
| `2-format-gallery/` | 7 | ❌ | **Input-format breadth** — clean CSV, messy CSV, XLSX, HTML email, and two **PDF factsheets** (the LLM document path). Metrics stay "pending" (no returns provided). |
| `3-scale-and-edge-cases/` | 120 | ✅ | **Scale + edge cases** — 120 funds with full return histories: a −92% drawdown fund, zero-volatility fund, low-confidence (short-history) flags, an unmatched fund, and a file that fails extraction on purpose. |

## Running the app

```bash
# backend
cd api && .venv/bin/uvicorn app.main:app --port 8000
# frontend (separate terminal)
cd web && npm run dev
```

The PDF (document) path and memo generation need an `ANTHROPIC_API_KEY` in a
`.env` (repo root or `api/`). Everything else works without one.
