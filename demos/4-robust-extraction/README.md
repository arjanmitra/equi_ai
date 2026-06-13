# Kit 4 — Robust extraction & the attribute bag · 6 funds

Stress-tests the two robustness features: **structure recovery** (the loader
finds the real table inside a hostile file instead of giving up) and the
**attribute bag** (columns that don't map to the schema are captured verbatim
as *source-attributed, untrusted* attributes — shown and citable, but never fed
into metrics or constraints).

All four universe variants describe the **same six funds**, so the one
`returns.csv` works with any of them:

> Meridian Global Macro · Lighthouse L/S Equity · Granite Credit Partners ·
> Solstice Managed Futures · Cobblestone Market Neutral · Tradewind Multi-Strategy

Run each universe file as its **own analysis** (don't upload two universe files
together — that would create duplicate funds). Attach `returns.csv` to whichever
one you're looking at.

---

## A · Structure recovery — `universe-structure-recovery.csv`

A CSV engineered to break a naive `read_csv`. Upload it → **Extract.** Every
defect below is recovered, and the **validation report** lists exactly what was
cleaned (look for the `structure:` notes):

| Injected defect | What recovery does |
|---|---|
| 2 comment/preamble lines before the header | skipped (header found on the real row) |
| 2 fully-blank rows (one mid-table) | dropped |
| Duplicate `Notes` column | de-duplicated → `Notes`, `Notes.1` |
| Lighthouse row has an extra trailing cell | ragged row reconciled (trimmed) |
| Granite row is missing its last two cells | ragged row reconciled (padded) |
| Leading/trailing whitespace in names | stripped |

**Expected:** all **6 funds** extract (path = `tabular`, *not* `none`), and the
de-duplicated `Notes.1` column shows up as an attribute (see B). Contrast with
Kit 3's `optional-adversarial-…csv`, which is the same class of file — it now
recovers too.

## B · Attribute bag — `universe-attribute-bag.csv`

A *clean* CSV, but it carries seven columns the canonical schema has no slot for:

> Sortino (reported) · Sharpe (reported) · ESG Rating · VaR 95% monthly ·
> PM Tenure (yrs) · Top-5 Concentration · Last Audit

Upload → **Extract**, then **click a fund row** in the extracted-data table.
Below its mapped fields you'll see an **"Additional attributes (as reported —
not validated, never used in metrics or constraints)"** panel, each value traced
to its exact source column.

The key demonstration is **`Sharpe (reported)`**: the manager's self-reported
Sharpe is captured as an attribute, while the app independently **computes its
own Sharpe** from `returns.csv`. The two live side by side — the reported one
can be *cited* in the memo (attributed to the manager) but can never override the
computed metric or a constraint check. That's the trust wall, made visible.

## C · Messy XLSX — `managers-messy.xlsx`

The same structure-recovery test, but in Excel: the real header sits on **row 4**
under two title rows + a blank spacer. Proves the recovery runs on the XLSX path,
not just CSV. (It also carries `Sharpe (reported)` and `ESG Rating` as attributes.)

---

## Suggested mandate (fires a computed constraint)

- Max management fee: **1.8%**
- Excluded strategies: **Managed Futures**
- Target volatility: **10%**

**Expected:** **Solstice** is excluded twice over — by the strategy rule *and*
by the computed-volatility rule (its return series is the most volatile, ~25%+
annualized, well above the 10% target). Note how its **reported Sortino (0.60)**
sits in the appendix as an as-reported attribute but plays **no part** in the
exclusion — the decision rests only on computed numbers.

## Generate the memo

Click **Generate IC memo**. In the memo, look for a sentence that quotes a
manager-reported attribute (e.g. *"the manager reports a Sharpe of 1.30"*) — its
citation chip traces to the `attribute:` source column, and it's phrased as
*reported*, never as the app's own figure.
