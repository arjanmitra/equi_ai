// Option lists + labels mirroring the backend enums (app/schemas/fund.py,
// evaluation.py). Kept hand-written for the scaffold.

export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const STRATEGY_OPTIONS: { value: string; label: string }[] = [
  { value: "long_short_equity", label: "L/S Equity" },
  { value: "market_neutral", label: "Market Neutral" },
  { value: "global_macro", label: "Global Macro" },
  { value: "managed_futures", label: "Managed Futures" },
  { value: "event_driven", label: "Event Driven" },
  { value: "credit", label: "Credit" },
  { value: "relative_value", label: "Relative Value" },
  { value: "multi_strategy", label: "Multi-Strategy" },
  { value: "fixed_income", label: "Fixed Income" },
  { value: "other", label: "Other" },
];

export const FREQUENCY_OPTIONS: { value: string; label: string }[] = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "quarterly", label: "Quarterly" },
  { value: "semi_annual", label: "Semi-Annual" },
  { value: "annual", label: "Annual" },
];

// constraint id -> friendly label for the run results view.
export const CONSTRAINT_LABELS: Record<string, string> = {
  excluded_strategy: "Excluded strategy",
  redemption_frequency: "Liquidity (redemption)",
  notice_period: "Notice period",
  lockup: "Lockup",
  preferred_strategy: "Strategy preference",
  management_fee: "Management fee",
  performance_fee: "Performance fee",
  min_aum: "Minimum AUM",
  min_track_record: "Track record",
  target_volatility: "Target volatility",
  max_drawdown: "Max drawdown",
};

export function strategyLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return STRATEGY_OPTIONS.find((o) => o.value === value)?.label ?? value;
}
