# Kit 3 — Scale & edge cases · 120 funds

Shows the system holding up at volume, and surfaces its real boundaries.

## Upload, in order

1. **`universe.csv`** → **Extract.** (120 funds in one messy CSV.)
2. **Attach returns** — both files:
   - `returns.csv` — ~5,000 monthly observations across 119 funds (long format).
   - `returns-messy.csv` — has **gaps, a duplicate row, and "Phantom Capital LP"
     (not in the universe)** → shows unmatched-fund reporting and de-duplication.
3. **Compute metrics.** Watch the table fill with 120 funds — volatilities from
   **0% to ~66%**, a **−92% max-drawdown** fund (an injected wipeout month), a
   **zero-volatility** fund (Sharpe shows "—", handled, not a crash), and "low n"
   badges on funds with short histories.
4. **Mandate → Evaluate** ranks all 120.

> Generating a memo over 120 funds is a very large prompt — fine to try, but the
> small **Kit 1** is the better memo demo.

## The two deliberate boundaries (optional)

- **Duplicate fund names:** the universe contains one repeated name, so in the
  returns step you'll see **119 of 120** funds match (two funds, one name → they
  collide). This is the known entity-resolution limit, by design.

- **`optional-adversarial-DESIGNED-TO-FAIL.csv`** — **do not** upload this as a
  normal input. It has comment-line preamble, duplicate columns, and ragged rows.
  Upload it *only* to demonstrate that extraction **fails gracefully** (it reports
  the file couldn't be parsed rather than crashing or inventing data).
