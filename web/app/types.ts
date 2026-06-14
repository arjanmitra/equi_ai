// Mirrors api/app/schemas/{extraction,mandate,evaluation}.py. Kept hand-written
// and small for the scaffold; a generated client (from the OpenAPI schema) is
// the next step.

export type IssueLevel = "info" | "flag" | "error";

export interface FieldIssue {
  level: IssueLevel;
  message: string;
  record_index: number | null;
  field: string | null;
}

export interface FieldProvenance {
  record_index: number;
  target_field: string;
  raw_value: unknown;
  normalized_value: unknown;
  source: string;
  transform: string | null;
  confidence: number | null;
  kind: "field" | "extra";
}

export interface ValidationReport {
  total_rows: number;
  records_ok: number;
  records_failed: number;
  unmapped_columns: string[];
  issues: FieldIssue[];
}

export interface ExtractionResult {
  source_name: string;
  target_schema: string;
  mime: string | null;
  strategy: "tabular" | "document" | "none";
  records: Record<string, unknown>[];
  provenance: FieldProvenance[];
  report: ValidationReport;
}

// --- Mapping review (plan / preview step) ----------------------------------

export type Transform =
  | "none"
  | "percent_to_decimal"
  | "bps_to_decimal"
  | "strip_currency"
  | "parse_date"
  | "parse_int"
  | "parse_float";

export interface ColumnMap {
  source_column: string;
  target_field: string;
  transform: Transform;
  confidence?: number | null;
  reasoning?: string | null;
}

export interface MappingPlan {
  mappings: ColumnMap[];
  unmapped_columns: string[];
}

export interface PlanFile {
  filename: string;
  strategy: "tabular" | "document" | "none";
  plan: MappingPlan | null;
  columns: string[];
  column_samples: Record<string, string[]>;
  preview: Record<string, unknown>[];
  structure_notes: string[];
  issues: FieldIssue[];
}

export interface PlanResponse {
  files: PlanFile[];
}

export interface FieldSpec {
  name: string;
  type: string;
  required: boolean;
  description?: string | null;
  enum_values?: string[] | null;
}

export interface TransformOption {
  value: string;
  label: string;
}

export interface SchemaResponse {
  target_fields: FieldSpec[];
  transforms: TransformOption[];
}

// --- Mandate + run ---------------------------------------------------------

export type View =
  | { kind: "analyses" }
  | { kind: "mandates" }
  | { kind: "analysis"; id: string; autoGenerate?: boolean }
  | { kind: "mandate"; id: string };

export interface AnalysisOut {
  id: string;
  created_at: string;
  label: string | null;
  upload_id: string;
  mandate_id: string | null;
  run_id: string | null;
  memo_id: string | null;
  universe_files: string[];
  returns_files: string[];
  has_memo: boolean;
}

export interface MandateOut {
  id: string;
  created_at: string;
  label: string | null;
  spec: MandateSpec;
}

export interface MemoSummary {
  id: string;
  run_id: string;
  created_at: string;
  model: string;
  all_verified: boolean;
  label: string | null;
}

export type Operator = "gte" | "lte" | "gt" | "lt" | "eq" | "neq" | "contains";

export interface CustomConstraint {
  id: string;
  label: string;
  attribute: string;
  value_type: "number" | "text";
  operator: Operator;
  threshold: number | string;
  severity: "hard" | "soft";
  penalty: number;
}

export interface MandateSpec {
  label?: string | null;
  max_redemption_frequency?: string | null;
  max_notice_period_days?: number | null;
  max_lockup_months?: number | null;
  max_management_fee?: number | null;
  max_performance_fee?: number | null;
  preferred_strategies: string[];
  excluded_strategies: string[];
  min_aum_usd?: number | null;
  min_track_record_months?: number | null;
  target_volatility?: number | null;
  max_drawdown?: number | null;
  severities?: Record<string, "hard" | "soft">;
  penalties?: Record<string, number>;
  custom_constraints?: CustomConstraint[];
}

export type CheckStatus = "pass" | "fail" | "na";
export type Severity = "hard" | "soft";

export interface ConstraintCheck {
  constraint: string;
  severity: Severity;
  status: CheckStatus;
  actual: unknown;
  threshold: unknown;
  penalty: number;
  reason: string;
  source_fields: string[];
}

export interface FundEvaluationOut {
  fund_id: string;
  fund_name: string;
  business_key: string;
  passed: boolean;
  score: number;
  checks: ConstraintCheck[];
  sharpe: number | null;
  annualized_volatility: number | null;
  max_drawdown: number | null;
}

export interface RunOut {
  id: string;
  upload_id: string;
  mandate_id: string;
  created_at: string;
  evaluations: FundEvaluationOut[];
}

// --- Returns + metrics -----------------------------------------------------

export interface ReturnsIngestResult {
  source_name: string;
  shape: string;
  observations_written: number;
  matched_funds: string[];
  unmatched_refs: string[];
  period_start: string | null;
  period_end: string | null;
}

// --- Memo + audit ----------------------------------------------------------

export interface Fact {
  id: string;
  kind: string;
  name: string;
  label: string;
  value: unknown;
  display: string;
  fund_id: string | null;
  provenance: string | null;
  extra: Record<string, unknown>;
}

export interface FundFacts {
  fund_id: string;
  fund_name: string;
  business_key: string;
  rank: number;
  passed: boolean;
  score: number;
  fields: Fact[];
  metrics: Fact[];
  checks: Fact[];
  attributes: Fact[];
}

export interface MemoClaimOut {
  id: string;
  text: string;
  refs: string[];
  verified: boolean;
  issues: string[];
}

export interface MemoSectionOut {
  kind: string;
  title: string;
  claims: MemoClaimOut[];
}

export interface MemoOut {
  id: string;
  run_id: string;
  created_at: string;
  model: string;
  all_verified: boolean;
  log: string[];
  sections: MemoSectionOut[];
  facts: Record<string, Fact>;
  appendix: FundFacts[];
}

export interface FundOut {
  id: string;
  upload_id: string;
  source_file_id: string;
  business_key: string;
  name: string;
  strategy: string | null;
  redemption_frequency: string | null;
  notice_period_days: number | null;
  lockup_months: number | null;
  management_fee: number | null;
  performance_fee: number | null;
  aum_usd: number | null;
  inception_date: string | null;
  notes: string | null;
}

export interface SourceFieldOut {
  id: string;
  target_field: string;
  raw_value: string | null;
  normalized_value: unknown;
  source: string;
  transform: string | null;
  confidence: number | null;
  kind: "field" | "extra";
}

export interface FundMetricsOut {
  fund_id: string;
  fund_name: string;
  business_key: string;
  benchmark_ticker: string | null;
  n_obs: number;
  annualized_volatility: number | null;
  max_drawdown: number | null;
  annualized_return: number | null;
  cumulative_return: number | null;
  sharpe: number | null;
  correlation_benchmark: number | null;
  period_start: string | null;
  period_end: string | null;
  low_confidence: boolean;
  inputs: Record<string, unknown>;
}
