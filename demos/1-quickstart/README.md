# Kit 1 — Quickstart (the full lifecycle) · 5 funds

**Start here.** This is the smallest kit that exercises the whole system, and
it's small enough to read every number.

Funds: Alpha Macro Partners, Beacon L/S Equity, Cobalt Managed Futures,
Delta Credit Opportunities, Echo Multi-Strat.

## Upload, in order

1. **`universe.csv`** → **Extract.**
   (A messy *semicolon-delimited* CSV — shows the tabular extraction: fees like
   `2%` become `0.02`, `$1.2B` becomes a real number, dates get parsed, and every
   value gets a provenance row pointing back to its column.)

2. **Attach returns** — select all three at once:
   - `returns-alpha-12mo.csv` — gives **Alpha 12 months** of history, so its
     metrics are *not* low-confidence (this is the fund the risk check will act on).
   - `returns-extra-long.csv` — adds Beacon (2 months) **and "Zeta Opportunities,"
     which is not in the universe** → demonstrates the *"unmatched fund, reported
     not fatal"* message.
   - `returns-wide.csv` — adds Cobalt via the **wide-by-date** format (date columns
     instead of rows).

3. **Compute metrics.** Alpha shows ~18% annualized vol; the short-history funds
   get a "low n" badge.

## Suggested mandate (makes the risk check fire)

- Max management fee: **1.8%**
- Excluded strategies: **Managed Futures**
- Target volatility: **10%**

**Expected result:** **Alpha is Excluded** — its computed 18% volatility exceeds
the 10% target (a *live, computed* hard constraint), with a grounded reason.
Cobalt is excluded by the strategy rule. The short-history funds aren't penalized
on volatility (low-confidence → "not enforced").

4. **Generate IC memo** → "All claims grounded." Click any citation chip to trace
   a sentence back to a metric or the exact source column. Download PDF/DOCX.
