# Kit 1 — Quickstart (the full lifecycle) · 5 funds

**Start here.** The smallest kit that exercises the whole system, and small
enough to read every number.

Funds: Alpha Macro Partners, Beacon L/S Equity, Cobalt Managed Futures,
Delta Credit Opportunities, Echo Multi-Strat.

## What to upload (in the New Analysis wizard, Step 1)

- **Fund universe:** `universe.csv`
  A messy *semicolon-delimited* CSV. The extraction shows: `2%` → `0.02`,
  `$1.2B` → a real number, dates parsed, and every value gets a provenance row.
- **Monthly returns:** select **all three** at once —
  - `returns-alpha-12mo.csv` — gives **Alpha 12 months** of history, so its
    metrics are *not* low-confidence (this is the fund the risk check acts on).
  - `returns-extra-long.csv` — adds Beacon (2 months) **and "Zeta Opportunities,"
    which is not in the universe** → demonstrates *"unmatched fund, reported, not
    fatal."*
  - `returns-wide.csv` — adds Cobalt via the **wide-by-date** format (date
    columns instead of rows).

In **Step 2 (Review mapping)** the columns should already be mapped correctly —
confirm and continue. Alpha shows ~18% annualized vol; short-history funds get a
"low n" badge.

## Suggested mandate (Step 3 → Create new mandate)

- Max management fee: **1.8%**
- Excluded strategies: **Managed Futures**
- Target volatility: **10%**

**Expected result (Step 4):** **Alpha is Excluded** — its computed 18% volatility
exceeds the 10% target (a *live, computed* hard constraint), with a grounded
reason. Cobalt is excluded by the strategy rule. Short-history funds aren't
penalized on volatility (low-confidence → "not enforced").

## The memo

Click **Generate IC Memo** → "All claims grounded." Click any citation chip to
trace a sentence back to a metric or the exact source column. Download PDF/DOCX.
