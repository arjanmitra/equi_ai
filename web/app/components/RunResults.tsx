"use client";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { CONSTRAINT_LABELS } from "../constants";
import { num, pct } from "@/lib/format";
import type {
  CheckStatus,
  ConstraintCheck,
  FundEvaluationOut,
  RunOut,
} from "../types";

type BadgeVariant = "success" | "destructive" | "secondary";
const STATUS_VARIANT: Record<CheckStatus, BadgeVariant> = {
  pass: "success",
  fail: "destructive",
  na: "secondary",
};

export function RunResults({ run }: { run: RunOut }) {
  const passed = run.evaluations.filter((e) => e.passed).length;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-brand-green">Shortlist</CardTitle>
        <span className="text-sm text-muted-foreground">
          {passed} of {run.evaluations.length} funds pass the mandate
        </span>
      </CardHeader>
      <CardContent className="space-y-2">
        {run.evaluations.map((e, i) => (
          <div key={e.fund_id} className="rounded-lg border p-3">
            <div className="flex items-center gap-3">
              <span className="w-6 text-sm text-muted-foreground">#{i + 1}</span>
              <span className="flex-1 font-medium">{e.fund_name}</span>
              <Badge variant={e.passed ? "success" : "destructive"}>
                {e.passed ? "Shortlisted" : "Excluded"}
              </Badge>
              <ScoreBar score={e.score} />
            </div>

            <MetricsLine e={e} />

            <details className="mt-2 pl-9 text-sm">
              <summary className="cursor-pointer text-muted-foreground">
                {e.checks.length} constraint checks
              </summary>
              <ul className="mt-2 space-y-1">
                {e.checks.map((c, j) => (
                  <CheckRow key={j} check={c} />
                ))}
              </ul>
            </details>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function MetricsLine({ e }: { e: FundEvaluationOut }) {
  if (e.sharpe == null && e.annualized_volatility == null && e.max_drawdown == null) {
    return null;
  }
  return (
    <div className="mt-1 pl-9 text-xs text-muted-foreground">
      Sharpe {num(e.sharpe)} · vol {pct(e.annualized_volatility)} · max DD{" "}
      {pct(e.max_drawdown)}
    </div>
  );
}

function CheckRow({ check }: { check: ConstraintCheck }) {
  const label = CONSTRAINT_LABELS[check.constraint] ?? check.constraint;
  return (
    <li className="flex flex-wrap items-center gap-2">
      <Badge variant={STATUS_VARIANT[check.status]}>{check.status}</Badge>
      <span className="text-xs font-medium text-muted-foreground">
        {check.severity}
      </span>
      <span className="font-medium text-foreground">{label}:</span>
      <span className="text-muted-foreground">{check.reason}</span>
      {check.penalty > 0 && (
        <span className="text-xs text-destructive">−{check.penalty}</span>
      )}
    </li>
  );
}

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-secondary">
        <div
          className="h-full rounded-full bg-brand-green"
          style={{ width: `${Math.max(0, Math.min(100, score))}%` }}
        />
      </div>
      <span className="w-8 text-right text-sm tabular-nums text-muted-foreground">
        {Math.round(score)}
      </span>
    </div>
  );
}
