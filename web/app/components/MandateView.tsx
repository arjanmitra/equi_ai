"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  DEFAULT_PENALTY,
  DEFAULT_SEVERITY,
  operatorSymbol,
  strategyLabel,
} from "../constants";
import type { MandateOut, MandateSpec } from "../types";

export function MandateView({ mandate }: { mandate: MandateOut }) {
  const groups = constraintGroups(mandate.spec);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-brand-green">
          {mandate.label ?? "Mandate"}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Created {new Date(mandate.created_at).toLocaleString()} · each rule
          shows its severity (hard = eliminates, soft = penalty).
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {groups.map((g) => (
          <Card key={g.title}>
            <CardHeader>
              <CardTitle className="text-base text-brand-green">{g.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {g.rows.length === 0 ? (
                <p className="text-sm text-muted-foreground">Not constrained</p>
              ) : (
                g.rows.map((r) => (
                  <div key={r.cid} className="flex items-center justify-between gap-2 text-sm">
                    <span className="text-muted-foreground">{r.label}</span>
                    <span className="flex items-center gap-2">
                      <span className="font-medium tabular-nums">{r.value}</span>
                      <SeverityChip spec={mandate.spec} cid={r.cid} />
                    </span>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        ))}

        {(mandate.spec.custom_constraints?.length ?? 0) > 0 && (
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="text-base text-brand-green">
                Custom attribute rules
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {mandate.spec.custom_constraints!.map((c) => (
                <div key={c.id} className="flex items-center justify-between gap-2 text-sm">
                  <span className="text-muted-foreground">
                    {c.label}{" "}
                    <span className="text-xs">(reported · {c.value_type})</span>
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="font-medium tabular-nums">
                      {operatorSymbol(c.operator)} {String(c.threshold)}
                    </span>
                    {c.severity === "hard" ? (
                      <Badge variant="secondary">hard</Badge>
                    ) : (
                      <Badge variant="outline">soft · −{c.penalty}</Badge>
                    )}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function SeverityChip({ spec, cid }: { spec: MandateSpec; cid: string }) {
  const severity = spec.severities?.[cid] ?? DEFAULT_SEVERITY[cid];
  const penalty = spec.penalties?.[cid] ?? DEFAULT_PENALTY[cid];
  if (severity === "hard") return <Badge variant="secondary">hard</Badge>;
  return <Badge variant="outline">soft · −{penalty}</Badge>;
}

type Row = { label: string; value: React.ReactNode; cid: string };

function constraintGroups(s: MandateSpec) {
  const pct = (v?: number | null) => (v == null ? null : `${(v * 100).toFixed(2)}%`);
  const money = (v?: number | null) =>
    v == null ? null : `$${(v / 1_000_000).toLocaleString()}M`;
  const strat = (arr: string[]) => (arr.length ? arr.map(strategyLabel).join(", ") : null);

  const rows = (entries: [string, React.ReactNode | null, string][]): Row[] =>
    entries
      .filter(([, v]) => v !== null && v !== undefined && v !== "")
      .map(([label, value, cid]) => ({ label, value, cid }));

  return [
    {
      title: "Liquidity",
      rows: rows([
        ["Min redemption frequency", s.max_redemption_frequency ?? null, "redemption_frequency"],
        ["Max notice (days)", s.max_notice_period_days ?? null, "notice_period"],
        ["Max lockup (months)", s.max_lockup_months ?? null, "lockup"],
      ]),
    },
    {
      title: "Fees",
      rows: rows([
        ["Max management fee", pct(s.max_management_fee), "management_fee"],
        ["Max performance fee", pct(s.max_performance_fee), "performance_fee"],
      ]),
    },
    {
      title: "Strategy",
      rows: rows([
        ["Preferred", strat(s.preferred_strategies), "preferred_strategy"],
        ["Excluded", strat(s.excluded_strategies), "excluded_strategy"],
      ]),
    },
    {
      title: "Size & track record",
      rows: rows([
        ["Min AUM", money(s.min_aum_usd), "min_aum"],
        ["Min track record (months)", s.min_track_record_months ?? null, "min_track_record"],
      ]),
    },
    {
      title: "Risk",
      rows: rows([
        ["Target volatility", pct(s.target_volatility), "target_volatility"],
        ["Max drawdown", pct(s.max_drawdown), "max_drawdown"],
      ]),
    },
  ];
}
