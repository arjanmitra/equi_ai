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

// Generic operators for promoted-attribute (custom) constraints.
export const OPERATOR_OPTIONS: { value: string; label: string; numeric: boolean }[] = [
  { value: "gte", label: "≥ (at least)", numeric: true },
  { value: "lte", label: "≤ (at most)", numeric: true },
  { value: "gt", label: "> (greater than)", numeric: true },
  { value: "lt", label: "< (less than)", numeric: true },
  { value: "eq", label: "= (equals)", numeric: false },
  { value: "neq", label: "≠ (not equals)", numeric: false },
  { value: "contains", label: "contains", numeric: false },
];

export function operatorSymbol(value: string): string {
  return { gte: "≥", lte: "≤", gt: ">", lt: "<", eq: "=", neq: "≠", contains: "contains" }[value] ?? value;
}

export function strategyLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return STRATEGY_OPTIONS.find((o) => o.value === value)?.label ?? value;
}

// Per-constraint defaults — must mirror engine.py's DEFAULT_SEVERITY / DEFAULT_PENALTY.
export type Severity = "hard" | "soft";

export const DEFAULT_SEVERITY: Record<string, Severity> = {
  redemption_frequency: "hard",
  notice_period: "hard",
  lockup: "hard",
  excluded_strategy: "hard",
  target_volatility: "hard",
  max_drawdown: "hard",
  preferred_strategy: "soft",
  management_fee: "soft",
  performance_fee: "soft",
  min_aum: "soft",
  min_track_record: "soft",
};

export const DEFAULT_PENALTY: Record<string, number> = {
  preferred_strategy: 15,
  management_fee: 10,
  performance_fee: 10,
  min_aum: 10,
  min_track_record: 10,
  redemption_frequency: 25,
  notice_period: 25,
  lockup: 25,
  excluded_strategy: 25,
  target_volatility: 25,
  max_drawdown: 25,
};
