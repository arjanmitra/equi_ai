"use client";

import { useState } from "react";
import { API } from "../constants";
import type { FundMetricsOut, ReturnsIngestResult } from "../types";
import { Badge, num, pct } from "./ui";

// Returns ingestion + metric computation for an upload. Self-contained: the
// backend persists metrics, so the mandate run reads them independently.
export function MetricsSection({ uploadId }: { uploadId: string }) {
  const [returnsFiles, setReturnsFiles] = useState<FileList | null>(null);
  const [ingests, setIngests] = useState<ReturnsIngestResult[] | null>(null);
  const [metrics, setMetrics] = useState<FundMetricsOut[] | null>(null);
  const [busy, setBusy] = useState<"returns" | "metrics" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function uploadReturns() {
    if (!returnsFiles?.length) return;
    setBusy("returns");
    setError(null);
    try {
      const form = new FormData();
      Array.from(returnsFiles).forEach((f) => form.append("files", f));
      const res = await fetch(`${API}/uploads/${uploadId}/returns`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      setIngests((await res.json()) as ReturnsIngestResult[]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Returns upload failed");
    } finally {
      setBusy(null);
    }
  }

  async function computeMetrics() {
    setBusy("metrics");
    setError(null);
    try {
      const res = await fetch(`${API}/uploads/${uploadId}/metrics`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ overrides: {} }),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      setMetrics((await res.json()) as FundMetricsOut[]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Metric computation failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
      <h2 className="font-medium">Returns &amp; metrics</h2>
      <p className="mt-1 text-sm text-slate-500">
        Attach a monthly return series (long or wide-by-date), then compute
        risk/return metrics. These power the mandate&apos;s volatility and
        drawdown checks.
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <input
          type="file"
          multiple
          accept=".csv,.tsv,.xlsx,.xls"
          onChange={(e) => setReturnsFiles(e.target.files)}
          className="text-sm"
        />
        <button
          onClick={uploadReturns}
          disabled={!returnsFiles?.length || busy !== null}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium disabled:opacity-40"
        >
          {busy === "returns" ? "Attaching…" : "Attach returns"}
        </button>
        <button
          onClick={computeMetrics}
          disabled={busy !== null}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-40"
        >
          {busy === "metrics" ? "Computing…" : "Compute metrics"}
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      {ingests && (
        <ul className="mt-4 space-y-1 text-sm">
          {ingests.map((r, i) => (
            <li key={i} className="flex flex-wrap items-center gap-2">
              <Badge tone="slate">{r.shape}</Badge>
              <span className="text-slate-600">
                {r.source_name}: {r.observations_written} observations,{" "}
                {r.matched_funds.length} fund(s) matched
                {r.period_start && `, ${r.period_start} → ${r.period_end}`}
              </span>
              {r.unmatched_refs.length > 0 && (
                <Badge tone="amber">
                  {r.unmatched_refs.length} unmatched
                </Badge>
              )}
            </li>
          ))}
        </ul>
      )}

      {metrics && <MetricsTable metrics={metrics} />}
    </section>
  );
}

function MetricsTable({ metrics }: { metrics: FundMetricsOut[] }) {
  return (
    <div className="mt-5 overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b text-left text-slate-500">
            <th className="px-2 py-1 font-medium">Fund</th>
            <th className="px-2 py-1 font-medium">Bench</th>
            <th className="px-2 py-1 font-medium text-right">n</th>
            <th className="px-2 py-1 font-medium text-right">Vol</th>
            <th className="px-2 py-1 font-medium text-right">Max DD</th>
            <th className="px-2 py-1 font-medium text-right">CAGR</th>
            <th className="px-2 py-1 font-medium text-right">Sharpe</th>
            <th className="px-2 py-1 font-medium text-right">Corr</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m) => (
            <tr key={m.fund_id} className="border-b last:border-0">
              <td className="px-2 py-1">
                {m.fund_name}
                {m.low_confidence && m.n_obs > 0 && (
                  <span className="ml-2">
                    <Badge tone="amber">low n</Badge>
                  </span>
                )}
              </td>
              <td className="px-2 py-1 text-slate-500">{m.benchmark_ticker ?? "—"}</td>
              <td className="px-2 py-1 text-right tabular-nums">{m.n_obs}</td>
              <td className="px-2 py-1 text-right tabular-nums">{pct(m.annualized_volatility)}</td>
              <td className="px-2 py-1 text-right tabular-nums">{pct(m.max_drawdown)}</td>
              <td className="px-2 py-1 text-right tabular-nums">{pct(m.annualized_return)}</td>
              <td className="px-2 py-1 text-right tabular-nums">{num(m.sharpe)}</td>
              <td className="px-2 py-1 text-right tabular-nums">{num(m.correlation_benchmark)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-slate-400">
        Vol annualized (×√12); CAGR geometric; Sharpe vs risk-free; corr vs
        benchmark. &quot;low n&quot; = under 12 months — risk checks report n/a.
      </p>
    </div>
  );
}
