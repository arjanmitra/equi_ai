// Mirrors api/app/schemas/extraction.py. Kept hand-written and small for the
// scaffold; a generated client (e.g. from the OpenAPI schema) is the next step.

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
  strategy: "tabular" | "document" | "none";
  records: Record<string, unknown>[];
  provenance: FieldProvenance[];
  report: ValidationReport;
}
