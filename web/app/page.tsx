"use client";

import { useState } from "react";
import { API } from "./constants";
import { MandateForm } from "./components/MandateForm";
import { MetricsSection } from "./components/MetricsSection";
import { RunResults } from "./components/RunResults";
import { Badge, Tone, format } from "./components/ui";
import type {
  ExtractionResult,
  FieldProvenance,
  IssueLevel,
  MandateSpec,
  RunOut,
} from "./types";

export default function Home() {
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
    } catch (e) {
      setRunError(e instanceof Error ? e.message : "Evaluation failed");
    } finally {
      setRunLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="text-2xl font-semibold">Allocator Memo Builder</h1>
      <p className="mt-1 text-sm text-slate-500">
        Upload a messy fund universe, set a mandate, and get a defendable,
        ranked shortlist — every verdict traced to a computed check or source
        field.
      </p>

      <div className="mt-6 flex items-center gap-3 rounded-lg border border-dashed border-slate-300 bg-white p-5">
        <input
          type="file"
          multiple
          accept=".csv,.tsv,.xlsx,.xls,.html,.htm,.pdf"
          onChange={(e) => setFiles(e.target.files)}
          className="text-sm"
        />
        <button
          onClick={onExtract}
          disabled={!files?.length || loading}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          {loading ? "Extracting…" : "Extract"}
        </button>
      </div>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      {uploadId && (
        <p className="mt-4 text-sm text-slate-500">
          Persisted as upload{" "}
          <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">
            {uploadId}
          </code>
        </p>
      )}

      {results?.map((r, i) => (
        <ResultCard key={i} result={r} />
      ))}

      {uploadId && <MetricsSection uploadId={uploadId} />}

      {uploadId && (
        <MandateForm onRun={onRun} loading={runLoading} error={runError} />
      )}

      {run && <RunResults run={run} />}
    </main>
  );
}

function ResultCard({ result }: { result: ExtractionResult }) {
  const { report } = result;
  const columns =
    result.records.length > 0 ? Object.keys(result.records[0]) : [];

  return (
    <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
      <header className="flex items-center justify-between">
        <h2 className="font-medium">{result.source_name}</h2>
        <div className="flex gap-2 text-xs">
          <Badge tone="slate">{result.strategy}</Badge>
          <Badge tone="green">{report.records_ok} ok</Badge>
          {report.records_failed > 0 && (
            <Badge tone="red">{report.records_failed} failed</Badge>
          )}
        </div>
      </header>

      {columns.length > 0 && (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b text-left text-slate-500">
                {columns.map((c) => (
                  <th key={c} className="px-2 py-1 font-medium">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.records.map((row, ri) => (
                <tr key={ri} className="border-b last:border-0">
                  {columns.map((c) => (
                    <td key={c} className="px-2 py-1">
                      {format(row[c])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ValidationPanel issues={report.issues} unmapped={report.unmapped_columns} />
      <ProvenancePanel provenance={result.provenance} />
    </section>
  );
}

function ValidationPanel({
  issues,
  unmapped,
}: {
  issues: ExtractionResult["report"]["issues"];
  unmapped: string[];
}) {
  if (issues.length === 0 && unmapped.length === 0) return null;
  return (
    <details className="mt-4 text-sm" open>
      <summary className="cursor-pointer font-medium text-slate-700">
        Validation report ({issues.length})
      </summary>
      {unmapped.length > 0 && (
        <p className="mt-2 text-slate-500">
          Unmapped columns: {unmapped.join(", ")}
        </p>
      )}
      <ul className="mt-2 space-y-1">
        {issues.map((it, i) => (
          <li key={i} className="flex gap-2">
            <Badge tone={toneFor(it.level)}>{it.level}</Badge>
            <span className="text-slate-600">{it.message}</span>
          </li>
        ))}
      </ul>
    </details>
  );
}

function ProvenancePanel({ provenance }: { provenance: FieldProvenance[] }) {
  if (provenance.length === 0) return null;
  return (
    <details className="mt-3 text-sm">
      <summary className="cursor-pointer font-medium text-slate-700">
        Provenance ({provenance.length}) — every value traced to its source
      </summary>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="border-b text-left text-slate-500">
              <th className="px-2 py-1">row</th>
              <th className="px-2 py-1">field</th>
              <th className="px-2 py-1">raw</th>
              <th className="px-2 py-1">normalized</th>
              <th className="px-2 py-1">source</th>
              <th className="px-2 py-1">transform</th>
            </tr>
          </thead>
          <tbody>
            {provenance.map((p, i) => (
              <tr key={i} className="border-b last:border-0">
                <td className="px-2 py-1">{p.record_index}</td>
                <td className="px-2 py-1 font-medium">{p.target_field}</td>
                <td className="px-2 py-1 text-slate-500">{format(p.raw_value)}</td>
                <td className="px-2 py-1">{format(p.normalized_value)}</td>
                <td className="px-2 py-1 text-slate-500">{p.source}</td>
                <td className="px-2 py-1 text-slate-400">{p.transform ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

function toneFor(level: IssueLevel): Tone {
  if (level === "error") return "red";
  if (level === "flag") return "amber";
  return "slate";
}
