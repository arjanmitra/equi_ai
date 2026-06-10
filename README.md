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
    db/                  SQLAlchemy: database.py (engine/session), models.py (ORM)
    services/            persistence.py (ExtractionResult -> rows)
    routers/             extract.py (ingest+persist), funds.py (read funds/provenance)
  tests/                 offline end-to-end + transform + persistence tests
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
cd api && .venv/bin/python -m pytest      # 30 tests, all offline
```

## Sample-data corpus (proving format-agnosticism)

One set of ground-truth funds, emitted in five deliberately-inconsistent shapes
— different column names, orders, delimiters, fee conventions (`2%` vs `150 bps`
vs bare `0.02`), AUM conventions (`$1.2B` vs `$1200M` vs full integer), date
formats, missing values, junk columns, and file types.

```bash
cd api
.venv/bin/python scripts/generate_corpus.py     # -> sample_data/
.venv/bin/python scripts/evaluate_corpus.py     # scores extraction vs ground truth
```

```
file                          path  records  precision  coverage
----------------------------------------------------------------
universe_clean.csv         tabular        7      100%      100%
universe_messy.csv         tabular        7      100%       96%   # withholds some values
managers.xlsx              tabular        4      100%      100%
manager_email.html         tabular        3      100%       75%   # carries a subset of fields
factsheet_alpha.pdf       document        1      100%      100%   # needs a key
factsheet_beacon.pdf      document        1      100%      100%   # needs a key
```

- **path** = which engine path ran. CSV/XLSX/HTML go through the deterministic
  `tabular` path; PDFs go through the LLM `document` path. Same six files, same
  canonical fields — that contrast *is* the type-agnostic proof.
- **precision** = of the values it extracted, how many are correct (the
  reliability headline — 100% across every format).
- **coverage** = how much of the schema it recovered; it drops legitimately when
  a source simply omits a field. "Missing ≠ wrong."

The two PDF factsheets are native-text PDFs that exercise the document path. They
need an `ANTHROPIC_API_KEY` (in a `.env` at the repo root or in `api/`) to read
field values; without one they're skipped and the offline formats still score.
`tests/test_corpus.py` runs the generate→extract→score loop as a regression on
every offline format, and is kept hermetic (it forces the offline path even when
a key is present), so the pytest gate never makes network calls.

## Deliberate scope cuts (to revisit)

- **Synchronous request/response**, no task queue — the flow stays legible for a
  take-home; production would move extraction + memo to a worker.
- **SQLite** (not yet wired) over BigQuery — right-sized, not over-engineered.
- **XLSX**: first non-empty sheet only; other sheets recorded, not merged.
- **No auth / multi-user / deployment.**

## Persistence & audit model (done)

Ingestion now persists into SQLite via SQLAlchemy. `POST /extract` writes one
transaction and returns an `upload_id`:

```
Upload ─1:N─> SourceFile ─1:N─> Fund ─1:N─> SourceField
```

- **Fund** mirrors the canonical schema as typed columns (queryable/filterable).
- **SourceField** is the provenance backbone — one row per extracted value, with
  both `raw_value` and `normalized_value` and where it came from. This is what
  the memo's audit trail will link claims back to.

Endpoints: `POST /extract` (ingest + persist), `GET /uploads/{id}`,
`GET /uploads/{id}/funds`, `GET /funds/{id}/provenance`. DB defaults to
`sqlite:///./equi_ai.db`; override with `DATABASE_URL` (Postgres-swappable). No
Alembic yet (scope cut); schema is created on startup. Persistence tests bind
their own in-memory SQLite, so the suite stays hermetic.

## Roadmap (next stages of the pipeline)

1. ~~Persist canonical funds + provenance (SQLAlchemy + SQLite).~~ ✓
2. Mandate form + constraint filtering (hybrid hard/soft; risk constraints
   modeled but deferred until metrics exist).
3. Benchmark fetch (yfinance) + risk-free rate (FRED) aligned to fund dates.
4. Deterministic metrics: vol, max drawdown, Sharpe, correlation (pure + tested).
5. Memo generation with a claim schema; reject-and-regenerate on ungrounded numbers.
6. Audit view: memo prose with inline citations back to a metric or source field.
