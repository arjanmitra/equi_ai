# Allocator Memo Builder

Take a messy, varied fund-universe dataset and a mandate, and produce a
**defendable** IC memo where every claim traces back to a computed metric or a
source field.

This repo is being built **Option B (the product) on top of Option A's
robust, type-agnostic extraction engine** (the CEO confirmed input formats vary,
so adaptable extraction is required). The organizing principle:

> The Python backend is a deterministic compute spine. The LLM only ever
> *narrates* values the code already produced or *recognizes* how to map a
> column — it never transcribes or invents numbers. That is what makes the
> audit trail real.

## What's built so far

The **extraction core** — the load-bearing wall both options need — plus a thin
upload UI that renders its output.

```
raw bytes ──► detect mime ──► loader ──► normalized intermediate
                                              │
                       ┌──────────────────────┴───────────────────────┐
                  TabularContent                                 DocumentContent
                       │                                               │
            mapping PLAN (LLM or heuristic)                  direct field extraction
            applied deterministically to                     (LLM reads values) +
            every row — LLM never sees values                repair loop on failure
                       │                                               │
                       └──────────────► Pydantic validate ◄───────────┘
                                              │
                              ExtractionResult{ records, provenance, report }
```

### The key design decision

**Tabular path → the LLM returns a mapping *plan*, not data.** It sees only the
headers and ~8 sample rows and decides which source column feeds which target
field and what transform to apply (`"Mgmt" → management_fee, percent_to_decimal`).
Code then applies that plan to all rows. The model is never in a position to get
a number wrong, and a 10,000-row file costs one cheap LLM call.

**Document path → direct extraction**, since there is no column grid. This is
the only path where the model reads values, so it carries the
repair loop and is where a future verification pass belongs.

**Provenance is captured at extraction time**, not bolted on later — that's what
powers Option B's claim-by-claim audit trail and Option A's "link to source doc."

## Repository layout

```
api/                     FastAPI + extraction engine (Python)
  app/
    schemas/             canonical Fund schema, extraction result types, mapping plan
    extraction/
      detect.py          mime sniffing from bytes
      transforms.py      deterministic cell transforms (% , currency, dates…)
      field_spec.py      turns a Pydantic target into a prompt/heuristic spec
      llm.py             Anthropic structured-output wrapper (tool use)
      validate.py        Pydantic coercion + soft/hard issue split
      repair.py          re-prompt-on-validation-error loop
      loaders/           csv / xlsx / html / pdf  → normalized intermediate
      mapping/
        tabular.py       the mapping-plan strategy
        document.py      direct field extraction
        heuristic.py     offline fallback so the tabular path needs no API key
      engine.py          extract(raw, filename, target) — the one entry point
    routers/extract.py   POST /extract
  tests/                 offline end-to-end + transform unit tests
web/                     Next.js (App Router) + Tailwind upload/results UI
```

## Run it

### Backend

```bash
cd api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp ../.env.example .env          # optional: add ANTHROPIC_API_KEY for PDF/doc + LLM mapping
.venv/bin/uvicorn app.main:app --reload --port 8000
```

The extraction core runs **offline with no API key** — the tabular path falls
back to a heuristic column matcher. A key unlocks LLM column mapping and the
document/PDF path.

### Frontend

```bash
cd web
npm install
cp .env.local.example .env.local
npm run dev          # http://localhost:3000
```

Upload `api/tests/fixtures/messy_universe.csv` to see the pipeline end-to-end:
semicolon delimiter sniffed, fees normalized to decimals, `$450M`/`$2.1B`
parsed, dates anchored, `fund_id` auto-derived, and full provenance.

### Tests

```bash
cd api && .venv/bin/python -m pytest
```

## Deliberate scope cuts (to revisit)

- **Synchronous request/response**, no task queue — the flow stays legible for a
  take-home; production would move extraction + memo to a worker.
- **SQLite** (not yet wired) over BigQuery — right-sized, not over-engineered.
- **XLSX**: first non-empty sheet only; other sheets recorded, not merged.
- **No auth / multi-user / deployment.**

## Roadmap (next stages of the pipeline)

1. Persist canonical funds + provenance (SQLAlchemy + SQLite).
2. Mandate form + constraint filtering.
3. Benchmark fetch (yfinance) + risk-free rate (FRED) aligned to fund dates.
4. Deterministic metrics: vol, max drawdown, Sharpe, correlation (pure + tested).
5. Memo generation with a claim schema; reject-and-regenerate on ungrounded numbers.
6. Audit view: memo prose with inline citations back to a metric or source field.
