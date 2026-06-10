"use client";

import { useState } from "react";
import { API } from "../constants";
import type { Fact, FundFacts, MemoClaimOut, MemoOut } from "../types";
import { Badge } from "./ui";

// Generate + read the IC memo. The reader renders each claim's citation chips;
// clicking one reveals the backing fact (value + provenance) — the audit view.
export function MemoPanel({ runId }: { runId: string }) {
  const [memo, setMemo] = useState<MemoOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/runs/${runId}/memo`, { method: "POST" });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail ?? `API ${res.status}`);
      }
      setMemo((await res.json()) as MemoOut);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Memo generation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
      <header className="flex items-center justify-between">
        <h2 className="font-medium">IC Memo</h2>
        {memo && (
          <div className="flex items-center gap-2 text-sm">
            <a
              href={`${API}/memos/${memo.id}/export?format=pdf`}
              className="rounded-md border border-slate-300 px-3 py-1 text-xs font-medium hover:bg-slate-50"
            >
              Download PDF
            </a>
            <a
              href={`${API}/memos/${memo.id}/export?format=docx`}
              className="rounded-md border border-slate-300 px-3 py-1 text-xs font-medium hover:bg-slate-50"
            >
              Download DOCX
            </a>
          </div>
        )}
      </header>

      {!memo && (
        <div className="mt-3">
          <p className="text-sm text-slate-500">
            Draft a defendable IC memo — every claim cites a computed metric or
            source field; ungrounded numbers are caught and regenerated.
          </p>
          <button
            onClick={generate}
            disabled={loading}
            className="mt-3 rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            {loading ? "Generating…" : "Generate IC memo"}
          </button>
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        </div>
      )}

      {memo && <MemoReader memo={memo} />}
    </section>
  );
}

function MemoReader({ memo }: { memo: MemoOut }) {
  const unverified = memo.sections
    .flatMap((s) => s.claims)
    .filter((c) => !c.verified).length;

  return (
    <div className="mt-3">
      <div className="flex items-center gap-2">
        <Badge tone={memo.all_verified ? "green" : "amber"}>
          {memo.all_verified
            ? "All claims grounded"
            : `${unverified} unverified`}
        </Badge>
        <span className="text-xs text-slate-400">
          {memo.model} · {new Date(memo.created_at).toLocaleDateString()}
        </span>
        <details className="ml-auto text-xs text-slate-400">
          <summary className="cursor-pointer">generation log</summary>
          <ul className="mt-1">
            {memo.log.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        </details>
      </div>

      {memo.sections.map((section, i) => (
        <div key={i} className="mt-5">
          <h3 className="text-sm font-semibold text-slate-700">
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
    <li className={`text-sm ${claim.verified ? "" : "rounded bg-amber-50 p-2"}`}>
      <p className="text-slate-700">
        {claim.text}
        {!claim.verified && (
          <span className="ml-2" title={claim.issues.join("; ")}>
            <Badge tone="amber">unverified</Badge>
          </span>
        )}
      </p>

      {claim.refs.length > 0 && (
        <div className="mt-1 flex flex-wrap gap-1">
          {claim.refs.map((ref) => {
            const f = facts[ref];
            if (!f) return null;
            return (
              <button
                key={ref}
                onClick={() => setOpenRef(openRef === ref ? null : ref)}
                className={`rounded border px-1.5 py-0.5 text-xs ${
                  openRef === ref
                    ? "border-blue-300 bg-blue-50 text-blue-700"
                    : "border-slate-200 bg-slate-50 text-slate-500 hover:bg-slate-100"
                }`}
                title={`${f.label} = ${f.display}`}
              >
                {f.label}
              </button>
            );
          })}
        </div>
      )}

      {open && (
        <div className="mt-2 rounded border border-blue-200 bg-blue-50/60 p-2 text-xs">
          <span className="font-medium text-slate-700">{open.label}</span>{" "}
          = <span className="tabular-nums">{open.display}</span>
          <span className="ml-2 rounded bg-white px-1 text-slate-400">
            {open.kind}
          </span>
          {open.provenance && (
            <div className="mt-0.5 text-slate-500">↳ {open.provenance}</div>
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
    <details className="mt-6 text-sm" open>
      <summary className="cursor-pointer text-sm font-semibold text-slate-700">
        Data appendix
      </summary>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="border-b text-left text-slate-500">
              <th className="px-2 py-1">#</th>
              <th className="px-2 py-1">Fund</th>
              <th className="px-2 py-1">Status</th>
              <th className="px-2 py-1">Strategy</th>
              <th className="px-2 py-1 text-right">AUM</th>
              <th className="px-2 py-1 text-right">Vol</th>
              <th className="px-2 py-1 text-right">Sharpe</th>
              <th className="px-2 py-1 text-right">Max DD</th>
            </tr>
          </thead>
          <tbody>
            {funds.map((ff) => (
              <tr key={ff.fund_id} className="border-b last:border-0">
                <td className="px-2 py-1">{ff.rank}</td>
                <td className="px-2 py-1">{ff.fund_name}</td>
                <td className="px-2 py-1">
                  <Badge tone={ff.passed ? "green" : "red"}>
                    {ff.passed ? "Shortlisted" : "Excluded"}
                  </Badge>
                </td>
                <td className="px-2 py-1 text-slate-500">
                  {get(ff.fields, "strategy")}
                </td>
                <td className="px-2 py-1 text-right">{get(ff.fields, "aum_usd")}</td>
                <td className="px-2 py-1 text-right">
                  {get(ff.metrics, "annualized_volatility")}
                </td>
                <td className="px-2 py-1 text-right">{get(ff.metrics, "sharpe")}</td>
                <td className="px-2 py-1 text-right">
                  {get(ff.metrics, "max_drawdown")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
