"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { API } from "../constants";
import type { Fact, FundFacts, MemoClaimOut, MemoOut } from "../types";

export function MemoReader({ memo }: { memo: MemoOut }) {
  const unverified = memo.sections
    .flatMap((s) => s.claims)
    .filter((c) => !c.verified).length;

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={memo.all_verified ? "success" : "warning"}>
          {memo.all_verified ? "All claims grounded" : `${unverified} unverified`}
        </Badge>
        <span className="text-xs text-muted-foreground">
          {memo.model} · {new Date(memo.created_at).toLocaleDateString()}
        </span>
        <div className="ml-auto flex items-center gap-2">
          <Button asChild variant="outline" size="sm">
            <a href={`${API}/memos/${memo.id}/export?format=pdf`}>Download PDF</a>
          </Button>
          <Button asChild variant="outline" size="sm">
            <a href={`${API}/memos/${memo.id}/export?format=docx`}>Download DOCX</a>
          </Button>
        </div>
      </div>

      <details className="mt-2 text-xs text-muted-foreground">
        <summary className="cursor-pointer">generation log</summary>
        <ul className="mt-1 list-disc pl-5">
          {memo.log.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      </details>

      {memo.sections.map((section, i) => (
        <div key={i} className="mt-5">
          <h3 className="text-sm font-semibold text-brand-green">
            {section.title}
          </h3>
          <ul className="mt-2 space-y-3">
            {section.claims.map((c) => (
              <ClaimView key={c.id} claim={c} facts={memo.facts} />
            ))}
          </ul>
        </div>
      ))}

      <Appendix funds={memo.appendix} />
    </div>
  );
}

function ClaimView({
  claim,
  facts,
}: {
  claim: MemoClaimOut;
  facts: Record<string, Fact>;
}) {
  const [openRef, setOpenRef] = useState<string | null>(null);
  const open = openRef ? facts[openRef] : null;

  return (
    <li
      className={`text-sm ${
        claim.verified ? "" : "rounded-md bg-amber-50 p-2"
      }`}
    >
      <p className="text-foreground">
        {claim.text}
        {!claim.verified && (
          <span className="ml-2 align-middle" title={claim.issues.join("; ")}>
            <Badge variant="warning">unverified</Badge>
          </span>
        )}
      </p>

      {claim.refs.length > 0 && (
        <div className="mt-1 flex flex-wrap gap-1">
          {claim.refs.map((ref) => {
            const f = facts[ref];
            if (!f) return null;
            const active = openRef === ref;
            return (
              <button
                key={ref}
                onClick={() => setOpenRef(active ? null : ref)}
                title={`${f.label} = ${f.display}`}
                className={`rounded border px-1.5 py-0.5 text-xs transition-colors ${
                  active
                    ? "border-primary bg-primary/10 text-brand-green"
                    : "border-border bg-secondary/50 text-muted-foreground hover:bg-secondary"
                }`}
              >
                {f.label}
              </button>
            );
          })}
        </div>
      )}

      {open && (
        <div className="mt-2 rounded-md border border-primary/40 bg-secondary/40 p-2 text-xs">
          <span className="font-medium text-brand-green">{open.label}</span> ={" "}
          <span className="tabular-nums">{open.display}</span>
          <Badge variant="outline" className="ml-2">
            {open.kind}
          </Badge>
          {open.provenance && (
            <div className="mt-0.5 text-muted-foreground">↳ {open.provenance}</div>
          )}
        </div>
      )}
    </li>
  );
}

function Appendix({ funds }: { funds: FundFacts[] }) {
  const get = (list: Fact[], name: string) =>
    list.find((f) => f.name === name)?.display ?? "—";

  return (
    <details className="mt-6" open>
      <summary className="cursor-pointer text-sm font-semibold text-brand-green">
        Data appendix
      </summary>
      <div className="mt-2 rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>#</TableHead>
              <TableHead>Fund</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Strategy</TableHead>
              <TableHead className="text-right">AUM</TableHead>
              <TableHead className="text-right">Vol</TableHead>
              <TableHead className="text-right">Sharpe</TableHead>
              <TableHead className="text-right">Max DD</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {funds.map((ff) => (
              <TableRow key={ff.fund_id}>
                <TableCell>{ff.rank}</TableCell>
                <TableCell className="font-medium">{ff.fund_name}</TableCell>
                <TableCell>
                  <Badge variant={ff.passed ? "success" : "destructive"}>
                    {ff.passed ? "Shortlisted" : "Excluded"}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {get(ff.fields, "strategy")}
                </TableCell>
                <TableCell className="text-right tabular-nums">{get(ff.fields, "aum_usd")}</TableCell>
                <TableCell className="text-right tabular-nums">{get(ff.metrics, "annualized_volatility")}</TableCell>
                <TableCell className="text-right tabular-nums">{get(ff.metrics, "sharpe")}</TableCell>
                <TableCell className="text-right tabular-nums">{get(ff.metrics, "max_drawdown")}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </details>
  );
}
