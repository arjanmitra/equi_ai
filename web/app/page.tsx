"use client";

import { useState } from "react";
import type { ExtractionResult, FieldProvenance, IssueLevel } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [files, setFiles] = useState<FileList | null>(null);
  const [results, setResults] = useState<ExtractionResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onExtract() {
    if (!files?.length) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const form = new FormData();
      Array.from(files).forEach((f) => form.append("files", f));
      const res = await fetch(`${API}/extract`, { method: "POST", body: form });
      if (!res.ok) throw new Error(`API ${res.status}`);
      setResults((await res.json()) as ExtractionResult[]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="text-2xl font-semibold">Allocator Memo Builder</h1>
      <p className="mt-1 text-sm text-slate-500">
        Step 1 — Upload a messy fund universe (CSV / XLSX / HTML / PDF). The
        engine maps any format onto the canonical fund schema and reports what it
        cleaned.
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

      {results?.map((r, i) => (
        <ResultCard key={i} result={r} />
      ))}
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

function Badge({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone: "slate" | "green" | "red" | "amber";
}) {
  const tones: Record<string, string> = {
    slate: "bg-slate-100 text-slate-700",
    green: "bg-green-100 text-green-700",
    red: "bg-red-100 text-red-700",
    amber: "bg-amber-100 text-amber-700",
  };
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

function toneFor(level: IssueLevel): "slate" | "green" | "red" | "amber" {
  if (level === "error") return "red";
  if (level === "flag") return "amber";
  return "slate";
}

function format(v: unknown): string {
  if (v === null || v === undefined) return "—";
  return String(v);
}
