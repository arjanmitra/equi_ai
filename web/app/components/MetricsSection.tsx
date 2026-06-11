"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
import { num, pct } from "@/lib/format";
import type { FundMetricsOut, ReturnsIngestResult } from "../types";

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
    <Card>
      <CardHeader>
        <CardTitle className="text-brand-green">Returns &amp; metrics</CardTitle>
        <CardDescription>
          Attach a monthly return series (long or wide-by-date), then compute
          risk/return metrics. These power the mandate&apos;s volatility and
          drawdown checks.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <Input
            type="file"
            multiple
            accept=".csv,.tsv,.xlsx,.xls"
            onChange={(e) => setReturnsFiles(e.target.files)}
            className="max-w-xs text-sm"
          />
          <Button
            variant="outline"
            onClick={uploadReturns}
            disabled={!returnsFiles?.length || busy !== null}
          >
            {busy === "returns" ? "Attaching…" : "Attach returns"}
          </Button>
          <Button onClick={computeMetrics} disabled={busy !== null}>
            {busy === "metrics" ? "Computing…" : "Compute metrics"}
          </Button>
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        {ingests && (
          <ul className="space-y-1 text-sm">
            {ingests.map((r, i) => (
              <li key={i} className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">{r.shape}</Badge>
                <span className="text-muted-foreground">
                  {r.source_name}: {r.observations_written} observations,{" "}
                  {r.matched_funds.length} fund(s) matched
                  {r.period_start && `, ${r.period_start} → ${r.period_end}`}
                </span>
                {r.unmatched_refs.length > 0 && (
                  <Badge variant="warning">
                    {r.unmatched_refs.length} unmatched
                  </Badge>
                )}
              </li>
            ))}
          </ul>
        )}

        {metrics && <MetricsTable metrics={metrics} />}
      </CardContent>
    </Card>
  );
}

function MetricsTable({ metrics }: { metrics: FundMetricsOut[] }) {
  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Fund</TableHead>
            <TableHead>Bench</TableHead>
            <TableHead className="text-right">n</TableHead>
            <TableHead className="text-right">Vol</TableHead>
            <TableHead className="text-right">Max DD</TableHead>
            <TableHead className="text-right">CAGR</TableHead>
            <TableHead className="text-right">Sharpe</TableHead>
            <TableHead className="text-right">Corr</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {metrics.map((m) => (
            <TableRow key={m.fund_id}>
              <TableCell className="font-medium">
                {m.fund_name}
                {m.low_confidence && m.n_obs > 0 && (
                  <Badge variant="warning" className="ml-2">
                    low n
                  </Badge>
                )}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {m.benchmark_ticker ?? "—"}
              </TableCell>
              <TableCell className="text-right tabular-nums">{m.n_obs}</TableCell>
              <TableCell className="text-right tabular-nums">{pct(m.annualized_volatility)}</TableCell>
              <TableCell className="text-right tabular-nums">{pct(m.max_drawdown)}</TableCell>
              <TableCell className="text-right tabular-nums">{pct(m.annualized_return)}</TableCell>
              <TableCell className="text-right tabular-nums">{num(m.sharpe)}</TableCell>
              <TableCell className="text-right tabular-nums">{num(m.correlation_benchmark)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
