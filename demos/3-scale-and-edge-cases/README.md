# Kit 3 — Scale & edge cases · 120 funds

Shows the system holding up at volume, and surfaces its real boundaries.

## What to upload (New Analysis wizard, Step 1)

- **Fund universe:** `universe.csv` — 120 funds in one messy CSV.
- **Monthly returns:** select **both** —
  - `returns.csv` — ~5,000 monthly observations across 119 funds (long format).
  - `returns-messy.csv` — has **gaps, a duplicate row, and "Phantom Capital LP"
    (not in the universe)** → shows unmatched-fund reporting and de-duplication.

Confirm the mapping in Step 2. The metrics fill out across 120 funds —
volatilities from **0% to ~66%**, a **−92% max-drawdown** fund (an injected
wipeout month), a **zero-volatility** fund (Sharpe shows "—", handled, not a
crash), and "low n" badges on short-history funds. In Step 3 attach any mandate;
Step 4 ranks all 120.

> Generating a memo over 120 funds is a very large prompt — fine to try, but the
> small **Kit 1** is the better memo demo.

## The two deliberate boundaries (optional)

- **Duplicate fund names:** the universe contains one repeated name, so you'll see
  **119 of 120** funds match on returns (two funds, one name → they collide). This
  is the known entity-resolution limit, by design.

- **`optional-adversarial-DESIGNED-TO-FAIL.csv`** — comment-line preamble,
  duplicate columns, ragged rows. The name is now a misnomer: with **structure
  recovery** this file *recovers* instead of failing — it extracts the funds and
  the validation report lists what it cleaned (preamble skipped, columns
  de-duplicated, ragged rows reconciled). For a kit built around these features,
  see **Kit 4 — Robust extraction & the attribute bag.**
