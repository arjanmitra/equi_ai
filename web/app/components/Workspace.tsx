"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { API } from "../constants";
import { cell } from "@/lib/format";
import type {
  ExtractionResult,
  FieldProvenance,
  IssueLevel,
  MandateSpec,
  RunOut,
} from "../types";
import { MandateForm } from "./MandateForm";
import { MemoPanel } from "./MemoPanel";
import { MetricsSection } from "./MetricsSection";
import { RunResults } from "./RunResults";

type IssueVariant = "destructive" | "warning" | "secondary";
const ISSUE_VARIANT: Record<IssueLevel, IssueVariant> = {
  error: "destructive",
  flag: "warning",
  info: "secondary",
};

export function Workspace({ onChanged }: { onChanged: () => void }) {
  const [files, setFiles] = useState<FileList | null>(null);
  const [results, setResults] = useState<ExtractionResult[] | null>(null);
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [run, setRun] = useState<RunOut | null>(null);
  const [runLoading, setRunLoading] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  async function onExtract() {
    if (!files?.length) return;
    setLoading(true);
    setError(null);
    setResults(null);
    setUploadId(null);
    setRun(null);
    try {
      const form = new FormData();
      Array.from(files).forEach((f) => form.append("files", f));
      const res = await fetch(`${API}/extract`, { method: "POST", body: form });
      if (!res.ok) throw new Error(`API ${res.status}`);
      const body = (await res.json()) as {
        upload_id: string;
        results: ExtractionResult[];
      };
      setUploadId(body.upload_id);
      setResults(body.results);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  async function onRun(spec: MandateSpec) {
    if (!uploadId) return;
    setRunLoading(true);
    setRunError(null);
    setRun(null);
    try {
      const res = await fetch(`${API}/uploads/${uploadId}/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mandate: spec }),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      setRun((await res.json()) as RunOut);
      onChanged(); // a new mandate was created
    } catch (e) {
      setRunError(e instanceof Error ? e.message : "Evaluation failed");
    } finally {
      setRunLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-brand-green">New analysis</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload a messy fund universe, set a mandate, and get a defendable,
          ranked shortlist — every verdict traced to a computed check or source
          field.
        </p>
      </div>

      <Card>
        <CardContent className="flex flex-wrap items-center gap-3 pt-6">
          <Input
            type="file"
            multiple
            accept=".csv,.tsv,.xlsx,.xls,.html,.htm,.pdf"
            onChange={(e) => setFiles(e.target.files)}
            className="max-w-sm"
          />
          <Button onClick={onExtract} disabled={!files?.length || loading}>
            {loading ? "Extracting…" : "Extract"}
          </Button>
          {error && <p className="text-sm text-destructive">{error}</p>}
          {uploadId && (
            <span className="text-sm text-muted-foreground">
              Persisted as{" "}
              <code className="rounded bg-secondary px-1.5 py-0.5 text-xs">
                {uploadId.slice(0, 8)}
              </code>
            </span>
          )}
        </CardContent>
      </Card>

      {results?.map((r, i) => (
        <ResultCard key={i} result={r} />
      ))}

      {uploadId && <MetricsSection uploadId={uploadId} />}
      {uploadId && (
        <MandateForm onRun={onRun} loading={runLoading} error={runError} />
      )}
      {run && <RunResults run={run} />}
      {run && <MemoPanel runId={run.id} onCreated={onChanged} />}
    </div>
  );
}

function ResultCard({ result }: { result: ExtractionResult }) {
  const { report } = result;
  const columns =
    result.records.length > 0 ? Object.keys(result.records[0]) : [];

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-brand-green">{result.source_name}</CardTitle>
        <div className="flex gap-2">
          <Badge variant="secondary">{result.strategy}</Badge>
          <Badge variant="success">{report.records_ok} ok</Badge>
          {report.records_failed > 0 && (
            <Badge variant="destructive">{report.records_failed} failed</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {columns.length > 0 && (
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  {columns.map((c) => (
                    <TableHead key={c}>{c}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {result.records.map((row, ri) => (
                  <TableRow key={ri}>
                    {columns.map((c) => (
                      <TableCell key={c}>{cell(row[c])}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {(report.issues.length > 0 || report.unmapped_columns.length > 0) && (
          <details className="text-sm" open>
            <summary className="cursor-pointer font-medium text-foreground">
              Validation report ({report.issues.length})
            </summary>
            {report.unmapped_columns.length > 0 && (
              <p className="mt-2 text-muted-foreground">
                Unmapped columns: {report.unmapped_columns.join(", ")}
              </p>
            )}
            <ul className="mt-2 space-y-1">
              {report.issues.map((it, i) => (
                <li key={i} className="flex items-center gap-2">
                  <Badge variant={ISSUE_VARIANT[it.level]}>{it.level}</Badge>
                  <span className="text-muted-foreground">{it.message}</span>
                </li>
              ))}
            </ul>
          </details>
        )}

        <ProvenancePanel provenance={result.provenance} />
      </CardContent>
    </Card>
  );
}

function ProvenancePanel({ provenance }: { provenance: FieldProvenance[] }) {
  if (provenance.length === 0) return null;
  return (
    <details className="text-sm">
      <summary className="cursor-pointer font-medium text-foreground">
        Provenance ({provenance.length}) — every value traced to its source
      </summary>
      <div className="mt-2 rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>row</TableHead>
              <TableHead>field</TableHead>
              <TableHead>raw</TableHead>
              <TableHead>normalized</TableHead>
              <TableHead>source</TableHead>
              <TableHead>transform</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {provenance.map((p, i) => (
              <TableRow key={i}>
                <TableCell>{p.record_index}</TableCell>
                <TableCell className="font-medium">{p.target_field}</TableCell>
                <TableCell className="text-muted-foreground">{cell(p.raw_value)}</TableCell>
                <TableCell>{cell(p.normalized_value)}</TableCell>
                <TableCell className="text-muted-foreground">{p.source}</TableCell>
                <TableCell className="text-muted-foreground">{p.transform ?? "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </details>
  );
}
