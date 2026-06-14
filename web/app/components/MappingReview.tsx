"use client";

import { Badge } from "@/components/ui/badge";
import { cell } from "@/lib/format";
import { cn } from "@/lib/utils";
import type {
  ColumnMap,
  MappingPlan,
  PlanFile,
  SchemaResponse,
  Transform,
} from "../types";

const DONT_MAP = "";

/** Review + edit the inferred column→field mapping before committing. Edits are
 *  emitted upward; the parent re-previews (no LLM) so the table below stays
 *  faithful to what will actually be persisted. */
export function MappingReview({
  files,
  plans,
  schema,
  onEdit,
  previewBusy,
}: {
  files: PlanFile[];
  plans: Record<string, MappingPlan>;
  schema: SchemaResponse;
  onEdit: (filename: string, plan: MappingPlan) => void;
  previewBusy?: boolean;
}) {
  const tabular = files.filter((f) => f.strategy === "tabular" && plans[f.filename]);
  const others = files.filter((f) => f.strategy !== "tabular");

  return (
    <div className="space-y-5">
      {previewBusy && (
        <p className="text-xs text-muted-foreground">Updating preview…</p>
      )}
      {tabular.map((f) => (
        <FileReview
          key={f.filename}
          file={f}
          plan={plans[f.filename]}
          schema={schema}
          onEdit={onEdit}
        />
      ))}
      {others.map((f) => (
        <p key={f.filename} className="text-xs text-muted-foreground">
          <span className="font-medium text-foreground">{f.filename}</span> —{" "}
          {f.strategy === "document"
            ? "document path, no columns to map (values read on commit)."
            : "could not be parsed as a table."}
        </p>
      ))}
    </div>
  );
}

function FileReview({
  file,
  plan,
  schema,
  onEdit,
}: {
  file: PlanFile;
  plan: MappingPlan;
  schema: SchemaResponse;
  onEdit: (filename: string, plan: MappingPlan) => void;
}) {
  const mapOf = (col: string) => plan.mappings.find((m) => m.source_column === col);
  const mappedFields = plan.mappings.map((m) => m.target_field);
  const nameMapped = mappedFields.includes("name");

  function emit(mappings: ColumnMap[]) {
    onEdit(file.filename, {
      mappings,
      unmapped_columns: file.columns.filter(
        (c) => !mappings.some((m) => m.source_column === c)
      ),
    });
  }

  function setField(col: string, field: string) {
    let mappings = plan.mappings.filter((m) => m.source_column !== col);
    if (field) {
      const existing = mapOf(col);
      mappings = [
        ...mappings,
        {
          source_column: col,
          target_field: field,
          transform: existing?.transform ?? "none",
          confidence: null,
        },
      ];
    }
    emit(mappings);
  }

  function setTransform(col: string, t: Transform) {
    emit(plan.mappings.map((m) => (m.source_column === col ? { ...m, transform: t } : m)));
  }

  const previewFields = schema.target_fields
    .map((f) => f.name)
    .filter((n) => mappedFields.includes(n));
  const flags = file.issues.filter((i) => i.level === "flag" || i.level === "error");

  return (
    <div className="rounded-lg border">
      <div className="flex items-center justify-between border-b bg-secondary/40 px-3 py-2">
        <span className="text-sm font-medium text-brand-green">{file.filename}</span>
        <span className="text-xs text-muted-foreground">
          {file.columns.length} columns
        </span>
      </div>

      {file.structure_notes.length > 0 && (
        <div className="flex flex-wrap gap-1.5 border-b px-3 py-2">
          {file.structure_notes.map((n, i) => (
            <Badge key={i} variant="outline" className="text-[11px] font-normal">
              {n}
            </Badge>
          ))}
        </div>
      )}

      {!nameMapped && (
        <p className="border-b bg-destructive/10 px-3 py-1.5 text-xs text-destructive">
          No column is mapped to <span className="font-medium">name</span> — rows
          without a fund name will be dropped.
        </p>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-muted-foreground">
              <th className="px-3 py-1.5 font-medium">Source column</th>
              <th className="px-3 py-1.5 font-medium">Sample values</th>
              <th className="px-3 py-1.5 font-medium">Maps to field</th>
              <th className="px-3 py-1.5 font-medium">Transform</th>
            </tr>
          </thead>
          <tbody>
            {file.columns.map((col) => {
              const m = mapOf(col);
              const samples = (file.column_samples[col] ?? []).slice(0, 3).join(", ");
              return (
                <tr key={col} className="border-t">
                  <td className="px-3 py-1.5 font-medium">{col}</td>
                  <td className="max-w-[160px] truncate px-3 py-1.5 text-muted-foreground">
                    {samples || "—"}
                  </td>
                  <td className="px-3 py-1.5">
                    <div className="flex items-center gap-1.5">
                      <select
                        value={m?.target_field ?? DONT_MAP}
                        onChange={(e) => setField(col, e.target.value)}
                        className="h-8 rounded border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                      >
                        <option value={DONT_MAP}>— don&apos;t map —</option>
                        {schema.target_fields.map((f) => (
                          <option key={f.name} value={f.name}>
                            {f.name}
                          </option>
                        ))}
                      </select>
                      {m?.confidence != null && (
                        <Confidence value={m.confidence} />
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-1.5">
                    {m ? (
                      <select
                        value={m.transform}
                        onChange={(e) => setTransform(col, e.target.value as Transform)}
                        className="h-8 rounded border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                      >
                        {schema.transforms.map((t) => (
                          <option key={t.value} value={t.value}>
                            {t.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="border-t px-3 py-2">
        <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Preview · what gets extracted
        </p>
        {previewFields.length === 0 ? (
          <p className="text-xs text-muted-foreground">Nothing mapped yet.</p>
        ) : (
          <div className="overflow-x-auto rounded border">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-secondary/40 text-left text-muted-foreground">
                  {previewFields.map((f) => (
                    <th key={f} className="px-2 py-1 font-medium">{f}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {file.preview.map((row, i) => (
                  <tr key={i} className="border-t">
                    {previewFields.map((f) => (
                      <td key={f} className="px-2 py-1 tabular-nums">{cell(row[f])}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {flags.length > 0 && (
          <ul className="mt-2 space-y-0.5">
            {flags.slice(0, 6).map((f, i) => (
              <li key={i} className="text-[11px] text-destructive">
                {f.message}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function Confidence({ value }: { value: number }) {
  const low = value < 0.6;
  return (
    <Badge
      variant="outline"
      className={cn("text-[10px] font-normal", low && "border-amber-500 text-amber-600")}
    >
      {Math.round(value * 100)}%
    </Badge>
  );
}
