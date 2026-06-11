"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { strategyLabel } from "../constants";
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
          Created {new Date(mandate.created_at).toLocaleString()}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {groups.map((g) => (
          <Card key={g.title}>
            <CardHeader>
              <CardTitle className="text-base text-brand-green">
                {g.title}
              </CardTitle>
              <CardDescription>{g.severity}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {g.rows.length === 0 ? (
                <p className="text-sm text-muted-foreground">Not constrained</p>
              ) : (
                g.rows.map((r) => (
                  <div key={r.label} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{r.label}</span>
                    <span className="font-medium tabular-nums">{r.value}</span>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

type Row = { label: string; value: React.ReactNode };

function constraintGroups(s: MandateSpec) {
  const pct = (v?: number | null) => (v == null ? null : `${(v * 100).toFixed(2)}%`);
  const money = (v?: number | null) =>
    v == null ? null : `$${(v / 1_000_000).toLocaleString()}M`;
  const strat = (arr: string[]) =>
    arr.length ? arr.map(strategyLabel).join(", ") : null;

  const rows = (entries: [string, React.ReactNode | null][]): Row[] =>
    entries
      .filter(([, v]) => v !== null && v !== undefined && v !== "")
      .map(([label, value]) => ({ label, value }));

  return [
    {
      title: "Liquidity",
      severity: "Hard constraints",
      rows: rows([
        ["Min redemption frequency", s.max_redemption_frequency ?? null],
        ["Max notice (days)", s.max_notice_period_days ?? null],
        ["Max lockup (months)", s.max_lockup_months ?? null],
      ]),
    },
    {
      title: "Fees",
      severity: "Soft constraints",
      rows: rows([
        ["Max management fee", pct(s.max_management_fee)],
        ["Max performance fee", pct(s.max_performance_fee)],
      ]),
    },
    {
      title: "Strategy",
      severity: "Exclusions hard · preferences soft",
      rows: rows([
        ["Preferred", strat(s.preferred_strategies)],
        ["Excluded", strat(s.excluded_strategies)],
      ]),
    },
    {
      title: "Size & track record",
      severity: "Soft constraints",
      rows: rows([
        ["Min AUM", money(s.min_aum_usd)],
        ["Min track record (months)", s.min_track_record_months ?? null],
      ]),
    },
    {
      title: "Risk",
      severity: "Hard · needs computed metrics",
      rows: rows([
        ["Target volatility", pct(s.target_volatility)],
        ["Max drawdown", pct(s.max_drawdown)],
      ]),
    },
  ];
}
