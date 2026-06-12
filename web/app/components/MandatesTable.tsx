"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { strategyLabel } from "../constants";
import type { MandateOut, MandateSpec } from "../types";
import { MandateModal } from "./MandateModal";

const pct = (v?: number | null) => (v == null ? "—" : `${(v * 100).toFixed(2)}%`);
const money = (v?: number | null) => (v == null ? "—" : `$${(v / 1e6).toLocaleString()}M`);
const n = (v?: number | null) => (v == null ? "—" : String(v));
const list = (a: string[]) => (a.length ? a.map(strategyLabel).join(", ") : "—");

const COLS: { head: string; cell: (s: MandateSpec) => string }[] = [
  { head: "Redemption", cell: (s) => s.max_redemption_frequency ?? "—" },
  { head: "Max notice", cell: (s) => n(s.max_notice_period_days) },
  { head: "Max lockup", cell: (s) => n(s.max_lockup_months) },
  { head: "Max mgmt", cell: (s) => pct(s.max_management_fee) },
  { head: "Max perf", cell: (s) => pct(s.max_performance_fee) },
  { head: "Preferred", cell: (s) => list(s.preferred_strategies) },
  { head: "Excluded", cell: (s) => list(s.excluded_strategies) },
  { head: "Min AUM", cell: (s) => money(s.min_aum_usd) },
  { head: "Min track", cell: (s) => n(s.min_track_record_months) },
  { head: "Target vol", cell: (s) => pct(s.target_volatility) },
  { head: "Max DD", cell: (s) => pct(s.max_drawdown) },
];

export function MandatesTable({
  mandates,
  onOpenMandate,
  onChanged,
}: {
  mandates: MandateOut[];
  onOpenMandate: (id: string) => void;
  onChanged: () => void;
}) {
  const [modal, setModal] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-brand-green">Mandates</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Reusable constraint sets — click a row to view, or create a new one.
          </p>
        </div>
        <Button onClick={() => setModal(true)}>
          <Plus /> New mandate
        </Button>
      </div>

      <Card>
        <CardContent className="pt-6">
          {mandates.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">
              No mandates yet. Click “New mandate” to create one.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  {COLS.map((c) => (
                    <TableHead key={c.head}>{c.head}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {mandates.map((m) => (
                  <TableRow
                    key={m.id}
                    className="cursor-pointer"
                    onClick={() => onOpenMandate(m.id)}
                  >
                    <TableCell className="font-medium">
                      {m.label ?? `Mandate ${new Date(m.created_at).toLocaleDateString()}`}
                    </TableCell>
                    {COLS.map((c) => (
                      <TableCell key={c.head} className="whitespace-nowrap text-muted-foreground">
                        {c.cell(m.spec)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <MandateModal open={modal} onOpenChange={setModal} onSaved={() => onChanged()} />
    </div>
  );
}
