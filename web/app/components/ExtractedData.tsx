"use client";

import { Fragment, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { API } from "../constants";
import { cell, pct } from "@/lib/format";
import type { FundOut, SourceFieldOut } from "../types";

export function ExtractedData({ funds }: { funds: FundOut[] }) {
  const [openId, setOpenId] = useState<string | null>(null);
  const [prov, setProv] = useState<Record<string, SourceFieldOut[]>>({});

  async function toggle(id: string) {
    if (openId === id) {
      setOpenId(null);
      return;
    }
    setOpenId(id);
    if (!prov[id]) {
      const p = (await (await fetch(`${API}/funds/${id}/provenance`)).json()) as SourceFieldOut[];
      setProv((prev) => ({ ...prev, [id]: p }));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-brand-green">Extracted data</CardTitle>
        <CardDescription>
          {funds.length} funds — click a fund to trace each value back to its
          source column.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Fund</TableHead>
                <TableHead>Strategy</TableHead>
                <TableHead>Redemption</TableHead>
                <TableHead className="text-right">Mgmt</TableHead>
                <TableHead className="text-right">Perf</TableHead>
                <TableHead className="text-right">AUM</TableHead>
                <TableHead>Inception</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {funds.map((f) => (
                <Fragment key={f.id}>
                  <TableRow className="cursor-pointer" onClick={() => toggle(f.id)}>
                    <TableCell className="font-medium">{f.name}</TableCell>
                    <TableCell className="text-muted-foreground">{f.strategy ?? "—"}</TableCell>
                    <TableCell>{f.redemption_frequency ?? "—"}</TableCell>
                    <TableCell className="text-right tabular-nums">{pct(f.management_fee)}</TableCell>
                    <TableCell className="text-right tabular-nums">{pct(f.performance_fee)}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {f.aum_usd != null ? `$${f.aum_usd.toLocaleString()}` : "—"}
                    </TableCell>
                    <TableCell>{f.inception_date ?? "—"}</TableCell>
                  </TableRow>
                  {openId === f.id && (
                    <TableRow>
                      <TableCell colSpan={7} className="bg-secondary/30">
                        <ProvenanceList items={prov[f.id]} />
                      </TableCell>
                    </TableRow>
                  )}
                </Fragment>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

function ProvenanceList({ items }: { items?: SourceFieldOut[] }) {
  if (!items) return <p className="py-2 text-xs text-muted-foreground">Loading…</p>;
  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="text-left text-muted-foreground">
          <th className="py-1 pr-3 font-medium">field</th>
          <th className="py-1 pr-3 font-medium">raw → normalized</th>
          <th className="py-1 pr-3 font-medium">source</th>
          <th className="py-1 font-medium">transform</th>
        </tr>
      </thead>
      <tbody>
        {items.map((p) => (
          <tr key={p.id}>
            <td className="py-0.5 pr-3 font-medium">{p.target_field}</td>
            <td className="py-0.5 pr-3">
              <span className="text-muted-foreground">{cell(p.raw_value)}</span> → {cell(p.normalized_value)}
            </td>
            <td className="py-0.5 pr-3 text-muted-foreground">{p.source}</td>
            <td className="py-0.5 text-muted-foreground">{p.transform ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
