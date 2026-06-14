# Allocator Memo Builder

Take a messy, varied fund-universe dataset and a mandate, and produce a
**defendable** investment-committee memo where every claim traces back to a
computed metric or a source field.

- **Design & architecture:** [`docs/DESIGN.md`](docs/DESIGN.md)
- **Demo data (what to upload, and when):** [`demos/`](demos/)

---

## Prerequisites

- **Python 3.11+** and **Node 18+**
- An **`ANTHROPIC_API_KEY`** is optional. Without one, the app still runs
  end-to-end: the tabular extraction path falls back to a deterministic heuristic
  and market data is synthetic. A key unlocks LLM column-mapping, the PDF/document
  path, and memo generation.

## First-time setup

### 1. Backend (FastAPI)

```bash
cd api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp ../.env.example ../.env          # then optionally add your ANTHROPIC_API_KEY
.venv/bin/uvicorn app.main:app --reload --port 8000
```

The API serves on `http://localhost:8000`. The SQLite database
(`api/equi_ai.db`) is created automatically on first start.

### 2. Frontend (Next.js)

In a second terminal:

```bash
cd web
npm install
cp .env.local.example .env.local    # points the UI at http://localhost:8000
npm run dev
```

Open `http://localhost:3000` and click **New analysis** to start. See
[`demos/`](demos/) for ready-made files and exactly which to upload.

### 3. (Optional) configuration

All settings have working defaults; override in `.env` (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | _(none)_ | Enables LLM mapping, PDF path, memo generation |
| `MARKET_DATA` | `fixture` | `fixture` (synthetic, offline) or `live` (yfinance + FRED) |
| `DATABASE_URL` | `sqlite:///./equi_ai.db` | Swappable (e.g. Postgres) |
| `MAPPING_MODEL` / `DOCUMENT_MODEL` / `MEMO_MODEL` | Haiku / Sonnet / Opus | Per-stage model overrides |

> No migrations tool is wired. If you change a DB model,
> delete `api/equi_ai.db` and restart — it's recreated from the current schema.

## Tests

```bash
cd api && .venv/bin/python -m pytest        # ~160 tests, fully offline/hermetic
```

The suite forces the offline LLM heuristic and synthetic market data, so it never
makes network calls.

---

## Folder structure

```
equi_ai/
├── README.md                  ← you are here (setup + layout)
├── docs/
│   └── DESIGN.md              ← architecture, engines, principles, diagrams
├── demos/                     ← sample upload bundles (each kit has its own README)
│   ├── 1-quickstart/          ← start here: full lifecycle, 5 funds
│   ├── 2-format-gallery/      ← input-format breadth (CSV/XLSX/HTML/PDF)
│   ├── 3-scale-and-edge-cases/← 120 funds + edge cases
│   └── 4-robust-extraction/   ← structure recovery + attribute bag
│
├── api/                       ← FastAPI backend (the deterministic compute spine)
│   ├── requirements.txt
│   └── app/
│       ├── main.py            ← app + router wiring
│       ├── config.py          ← settings (env-driven)
│       ├── schemas/           ← Pydantic contracts: Fund, MandateSpec, mapping plan, …
│       ├── extraction/        ← EXTRACTION ENGINE
│       │   ├── engine.py      ← extract(raw, filename, target, plan) entry point
│       │   ├── detect.py      ← mime sniffing
│       │   ├── structure.py   ← grid/structure recovery (preamble, ragged, dup cols)
│       │   ├── loaders/       ← csv / xlsx / html / pdf → normalized intermediate
│       │   ├── mapping/       ← tabular (plan), document (direct), heuristic (offline)
│       │   ├── transforms.py  ← deterministic cell transforms (%, currency, dates)
│       │   ├── field_spec.py  ← Pydantic target → prompt/heuristic spec
│       │   ├── validate.py    ← coercion + soft/hard issue split
│       │   ├── repair.py      ← document-path re-prompt-on-error loop
│       │   └── llm.py         ← Anthropic structured-output (tool use) wrapper
│       ├── returns/ingest.py  ← RETURNS INGESTION (long + wide shapes, match by name)
│       ├── metrics/functions.py ← METRICS ENGINE (vol, drawdown, CAGR, Sharpe, corr)
│       ├── market/            ← market data providers (fixture | live) + cache
│       ├── constraints/engine.py ← CONSTRAINT ENGINE (hard/soft/na + scoring)
│       ├── memo/              ← MEMO ENGINE: catalog, generate, verify, numbers
│       ├── db/                ← SQLAlchemy: database.py (session), models.py (ORM)
│       ├── services/          ← orchestration: persistence, evaluation, metrics, memo, …
│       └── routers/           ← HTTP endpoints: extract, funds, mandates, runs, memo, …
│   └── tests/                 ← hermetic test suite
│
└── web/                       ← Next.js (App Router) + Tailwind + shadcn UI
    ├── app/
    │   ├── page.tsx           ← shell + view routing
    │   ├── types.ts           ← mirrors the backend schemas
    │   ├── constants.ts       ← option lists, labels, API base
    │   └── components/        ← AnalysesTable, NewAnalysisWizard, MappingReview,
    │                            MandateFields/Modal/View, RunResults, MemoReader, …
    └── components/ui/         ← shadcn primitives (Radix + Tailwind)
```
