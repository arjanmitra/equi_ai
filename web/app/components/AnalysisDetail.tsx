"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
import type {
  AnalysisOut,
  FundMetricsOut,
  FundOut,
  MemoOut,
  RunOut,
} from "../types";
import { ExtractedData } from "./ExtractedData";
import { MemoReader } from "./MemoReader";
import { RunResults } from "./RunResults";

const JSON_H = { "Content-Type": "application/json" };

export function AnalysisDetail({
  analysisId,
  autoGenerate,
  onBack,
  onChanged,
}: {
  analysisId: string;
  autoGenerate?: boolean;
  onBack: () => void;
  onChanged: () => void;
}) {
  const [analysis, setAnalysis] = useState<AnalysisOut | null>(null);
  const [funds, setFunds] = useState<FundOut[] | null>(null);
  const [metrics, setMetrics] = useState<FundMetricsOut[] | null>(null);
  const [run, setRun] = useState<RunOut | null>(null);
  const [memo, setMemo] = useState<MemoOut | null>(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = useCallback(async (runId: string, id: string) => {
    setGenerating(true);
    setError(null);
    try {
      const res = await fetch(`${API}/runs/${runId}/memo`, { method: "POST" });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `API ${res.status}`);
      }
      const m = (await res.json()) as MemoOut;
      setMemo(m);
      await fetch(`${API}/analyses/${id}`, { method: "PATCH", headers: JSON_H, body: JSON.stringify({ memo_id: m.id }) });
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Memo generation failed");
    } finally {
      setGenerating(false);
    }
  }, [onChanged]);

  useEffect(() => {
    let active = true;
    (async () => {
      setError(null);
      setMemo(null);
      try {
        const a = (await (await fetch(`${API}/analyses/${analysisId}`)).json()) as AnalysisOut;
        if (!active) return;
        setAnalysis(a);
        const [f, m] = await Promise.all([
          fetch(`${API}/uploads/${a.upload_id}/funds`).then((r) => r.json()),
          fetch(`${API}/uploads/${a.upload_id}/metrics`).then((r) => r.json()),
        ]);
        if (!active) return;
        setFunds(f as FundOut[]);
        setMetrics(m as FundMetricsOut[]);
        if (a.run_id) setRun((await (await fetch(`${API}/runs/${a.run_id}`)).json()) as RunOut);
        if (a.memo_id) {
          setMemo((await (await fetch(`${API}/memos/${a.memo_id}`)).json()) as MemoOut);
        } else if (autoGenerate && a.run_id) {
          generate(a.run_id, a.id);
        }
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : "Failed to load analysis");
      }
    })();
    return () => {
      active = false;
    };
  }, [analysisId, autoGenerate, generate]);

  return (
    <div className="space-y-6">
      <div>
        <Button variant="ghost" size="sm" onClick={onBack} className="-ml-2 mb-1">
          <ChevronLeft /> Back to analyses
        </Button>
        <h1 className="text-2xl font-semibold text-brand-green">
          {analysis?.label ?? "Analysis"}
        </h1>
        {analysis && (
          <p className="mt-1 text-sm text-muted-foreground">
            Universe: {analysis.universe_files.join(", ") || "—"}
            {analysis.returns_files.length > 0 && ` · Returns: ${analysis.returns_files.join(", ")}`}
          </p>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {funds && <ExtractedData funds={funds} />}

      {metrics && metrics.some((m) => m.n_obs > 0) && <MetricsCard metrics={metrics} />}

      {run && <RunResults run={run} />}

      <Card>
        <CardHeader>
          <CardTitle className="text-brand-green">IC Memo</CardTitle>
        </CardHeader>
        <CardContent>
          {memo ? (
            <MemoReader memo={memo} />
          ) : generating ? (
            <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Generating… (writing the
              memo and verifying every number against the computed facts)
            </div>
          ) : run ? (
            <Button onClick={() => analysis && run && generate(run.id, analysis.id)}>
              Generate IC memo
            </Button>
          ) : (
            <p className="text-sm text-muted-foreground">
              This analysis hasn&apos;t been evaluated against a mandate yet.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function MetricsCard({ metrics }: { metrics: FundMetricsOut[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-brand-green">Metrics</CardTitle>
      </CardHeader>
      <CardContent>
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
              {metrics
                .filter((m) => m.n_obs > 0)
                .map((m) => (
                  <TableRow key={m.fund_id}>
                    <TableCell className="font-medium">
                      {m.fund_name}
                      {m.low_confidence && (
                        <Badge variant="warning" className="ml-2">low n</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{m.benchmark_ticker ?? "—"}</TableCell>
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
      </CardContent>
    </Card>
  );
}
