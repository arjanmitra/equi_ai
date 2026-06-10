"use client";

import { CONSTRAINT_LABELS } from "../constants";
import type { CheckStatus, ConstraintCheck, RunOut } from "../types";
import { Badge, Tone } from "./ui";

const STATUS_TONE: Record<CheckStatus, Tone> = {
  pass: "green",
  fail: "red",
  na: "slate",
};

export function RunResults({ run }: { run: RunOut }) {
  const passed = run.evaluations.filter((e) => e.passed).length;

  return (
    <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
      <header className="flex items-center justify-between">
        <h2 className="font-medium">Shortlist</h2>
        <span className="text-sm text-slate-500">
          {passed} of {run.evaluations.length} funds pass the mandate
        </span>
      </header>

      <ul className="mt-4 space-y-2">
        {run.evaluations.map((e, i) => (
          <li
            key={e.fund_id}
            className="rounded-md border border-slate-200 p-3"
          >
            <div className="flex items-center gap-3">
              <span className="w-6 text-sm text-slate-400">#{i + 1}</span>
              <span className="flex-1 font-medium">{e.fund_name}</span>
              <Badge tone={e.passed ? "green" : "red"}>
                {e.passed ? "Shortlisted" : "Excluded"}
              </Badge>
              <ScoreBar score={e.score} />
            </div>

            <details className="mt-2 pl-9 text-sm">
              <summary className="cursor-pointer text-slate-500">
                {e.checks.length} constraint checks
              </summary>
              <ul className="mt-2 space-y-1">
                {e.checks.map((c, j) => (
                  <CheckRow key={j} check={c} />
                ))}
              </ul>
            </details>
          </li>
        ))}
      </ul>
    </section>
  );
}

function CheckRow({ check }: { check: ConstraintCheck }) {
  const label = CONSTRAINT_LABELS[check.constraint] ?? check.constraint;
  return (
    <li className="flex flex-wrap items-center gap-2">
      <Badge tone={STATUS_TONE[check.status]}>{check.status}</Badge>
      <span className="text-xs font-medium text-slate-500">{check.severity}</span>
      <span className="font-medium text-slate-700">{label}:</span>
      <span className="text-slate-600">{check.reason}</span>
      {check.penalty > 0 && (
        <span className="text-xs text-red-500">−{check.penalty}</span>
      )}
    </li>
  );
}

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 overflow-hidden rounded bg-slate-100">
        <div
          className="h-full rounded bg-slate-700"
          style={{ width: `${Math.max(0, Math.min(100, score))}%` }}
        />
      </div>
      <span className="w-8 text-right text-sm tabular-nums text-slate-600">
        {Math.round(score)}
      </span>
    </div>
  );
}
