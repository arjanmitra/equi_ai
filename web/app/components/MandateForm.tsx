"use client";

import { useState } from "react";
import { FREQUENCY_OPTIONS, STRATEGY_OPTIONS } from "../constants";
import type { MandateSpec } from "../types";
import { Section } from "./ui";

// The form keeps raw string inputs; we parse/convert on submit. Allocators think
// in % and $M, so fees are entered as percents and AUM in millions, then
// converted to the backend's decimals / absolute USD.

const numOrNull = (s: string): number | null =>
  s.trim() === "" ? null : Number(s);
const pctToDecimal = (s: string): number | null => {
  const n = numOrNull(s);
  return n === null ? null : n / 100;
};
const millionsToUsd = (s: string): number | null => {
  const n = numOrNull(s);
  return n === null ? null : n * 1_000_000;
};

export function MandateForm({
  onRun,
  loading,
  error,
}: {
  onRun: (spec: MandateSpec) => void;
  loading: boolean;
  error: string | null;
}) {
  const [label, setLabel] = useState("");
  const [redemption, setRedemption] = useState("");
  const [notice, setNotice] = useState("");
  const [lockup, setLockup] = useState("");
  const [mgmtFee, setMgmtFee] = useState("");
  const [perfFee, setPerfFee] = useState("");
  const [preferred, setPreferred] = useState<string[]>([]);
  const [excluded, setExcluded] = useState<string[]>([]);
  const [minAum, setMinAum] = useState("");
  const [trackRecord, setTrackRecord] = useState("");
  const [targetVol, setTargetVol] = useState("");
  const [maxDd, setMaxDd] = useState("");

  function toggle(list: string[], value: string): string[] {
    return list.includes(value)
      ? list.filter((v) => v !== value)
      : [...list, value];
  }

  function submit() {
    onRun({
      label: label || null,
      max_redemption_frequency: redemption || null,
      max_notice_period_days: numOrNull(notice),
      max_lockup_months: numOrNull(lockup),
      max_management_fee: pctToDecimal(mgmtFee),
      max_performance_fee: pctToDecimal(perfFee),
      preferred_strategies: preferred,
      excluded_strategies: excluded,
      min_aum_usd: millionsToUsd(minAum),
      min_track_record_months: numOrNull(trackRecord),
      target_volatility: pctToDecimal(targetVol),
      max_drawdown: pctToDecimal(maxDd),
    });
  }

  return (
    <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
      <h2 className="font-medium">Mandate</h2>
      <p className="mt-1 text-sm text-slate-500">
        Set the constraints. Leave a field blank to skip that check. Hard
        constraints (liquidity, exclusions) eliminate funds; soft ones (fees,
        preferences, size) lower the score.
      </p>

      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        <Section title="Liquidity (hard)">
          <Field label="Need at least this redemption frequency">
            <select
              className={inputClass}
              value={redemption}
              onChange={(e) => setRedemption(e.target.value)}
            >
              <option value="">Any</option>
              {FREQUENCY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Max notice period (days)">
            <NumberInput value={notice} onChange={setNotice} placeholder="e.g. 60" />
          </Field>
          <Field label="Max lockup (months)">
            <NumberInput value={lockup} onChange={setLockup} placeholder="e.g. 12" />
          </Field>
        </Section>

        <Section title="Fees (soft)">
          <Field label="Max management fee (%)">
            <NumberInput value={mgmtFee} onChange={setMgmtFee} placeholder="e.g. 1.8" />
          </Field>
          <Field label="Max performance fee (%)">
            <NumberInput value={perfFee} onChange={setPerfFee} placeholder="e.g. 20" />
          </Field>
        </Section>

        <Section title="Strategy" hint="Exclusions are hard; preferences are soft.">
          <p className="mb-1 text-xs font-medium text-slate-500">Preferred</p>
          <StrategyChecks selected={preferred} onToggle={(v) => setPreferred(toggle(preferred, v))} />
          <p className="mb-1 mt-3 text-xs font-medium text-slate-500">Excluded</p>
          <StrategyChecks selected={excluded} onToggle={(v) => setExcluded(toggle(excluded, v))} />
        </Section>

        <Section title="Size & track record (soft)">
          <Field label="Min AUM ($M)">
            <NumberInput value={minAum} onChange={setMinAum} placeholder="e.g. 100" />
          </Field>
          <Field label="Min track record (months)">
            <NumberInput value={trackRecord} onChange={setTrackRecord} placeholder="e.g. 36" />
          </Field>
        </Section>

        <Section
          title="Risk (pending metrics)"
          hint="Captured now; evaluated once the metrics stage computes vol & drawdown."
        >
          <Field label="Target volatility (%)">
            <NumberInput value={targetVol} onChange={setTargetVol} placeholder="e.g. 10" />
          </Field>
          <Field label="Max drawdown (%)">
            <NumberInput value={maxDd} onChange={setMaxDd} placeholder="e.g. 20" />
          </Field>
        </Section>

        <Section title="Label">
          <Field label="Mandate name (optional)">
            <input
              className={inputClass}
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g. Liquid macro sleeve"
            />
          </Field>
        </Section>
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      <button
        onClick={submit}
        disabled={loading}
        className="mt-4 rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
      >
        {loading ? "Evaluating…" : "Evaluate funds"}
      </button>
    </section>
  );
}

const inputClass =
  "w-full rounded border border-slate-300 px-2 py-1 text-sm focus:border-slate-500 focus:outline-none";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="mb-2 block">
      <span className="mb-1 block text-xs text-slate-500">{label}</span>
      {children}
    </label>
  );
}

function NumberInput({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <input
      type="number"
      className={inputClass}
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

function StrategyChecks({
  selected,
  onToggle,
}: {
  selected: string[];
  onToggle: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1">
      {STRATEGY_OPTIONS.map((o) => (
        <label key={o.value} className="flex items-center gap-1 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={selected.includes(o.value)}
            onChange={() => onToggle(o.value)}
          />
          {o.label}
        </label>
      ))}
    </div>
  );
}
