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

// --- Mandate + run ---------------------------------------------------------

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
}

export interface RunOut {
  id: string;
  upload_id: string;
  mandate_id: string;
  created_at: string;
  evaluations: FundEvaluationOut[];
}
