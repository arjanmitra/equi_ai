"use client";

import { useEffect, useState } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import {
  DEFAULT_PENALTY,
  DEFAULT_SEVERITY,
  FREQUENCY_OPTIONS,
  STRATEGY_OPTIONS,
  type Severity,
} from "../constants";
import type { MandateSpec } from "../types";

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

type SevMap = Record<string, Severity>;
type PenMap = Record<string, number>;

/** Controlled mandate inputs, incl. per-constraint hard/soft + penalty. Emits
 *  the built MandateSpec (with severities/penalties maps) on every change. */
export function MandateFields({
  onChange,
}: {
  onChange: (spec: MandateSpec) => void;
}) {
  const [label, setLabel] = useState("");
  const [redemption, setRedemption] = useState("any");
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

  const [sev, setSevState] = useState<SevMap>({ ...DEFAULT_SEVERITY });
  const [pen, setPenState] = useState<PenMap>({ ...DEFAULT_PENALTY });
  const setSev = (cid: string, v: Severity) => setSevState((p) => ({ ...p, [cid]: v }));
  const setPen = (cid: string, v: number) => setPenState((p) => ({ ...p, [cid]: v }));

  useEffect(() => {
    onChange({
      label: label || null,
      max_redemption_frequency: redemption === "any" ? null : redemption,
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
      severities: sev,
      penalties: pen,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [label, redemption, notice, lockup, mgmtFee, perfFee, preferred, excluded, minAum, trackRecord, targetVol, maxDd, sev, pen]);

  const toggle = (list: string[], v: string) =>
    list.includes(v) ? list.filter((x) => x !== v) : [...list, v];

  const sp = { sev, pen, setSev, setPen };

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <Group title="Liquidity">
        <ConstraintField label="Need at least this redemption frequency" cid="redemption_frequency" {...sp}>
          <Select value={redemption} onValueChange={setRedemption}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="any">Any</SelectItem>
              {FREQUENCY_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </ConstraintField>
        <ConstraintField label="Max notice period (days)" cid="notice_period" {...sp}>
          <Input type="number" value={notice} onChange={(e) => setNotice(e.target.value)} placeholder="e.g. 60" />
        </ConstraintField>
        <ConstraintField label="Max lockup (months)" cid="lockup" {...sp}>
          <Input type="number" value={lockup} onChange={(e) => setLockup(e.target.value)} placeholder="e.g. 12" />
        </ConstraintField>
      </Group>

      <Group title="Fees">
        <ConstraintField label="Max management fee (%)" cid="management_fee" {...sp}>
          <Input type="number" value={mgmtFee} onChange={(e) => setMgmtFee(e.target.value)} placeholder="e.g. 1.8" />
        </ConstraintField>
        <ConstraintField label="Max performance fee (%)" cid="performance_fee" {...sp}>
          <Input type="number" value={perfFee} onChange={(e) => setPerfFee(e.target.value)} placeholder="e.g. 20" />
        </ConstraintField>
      </Group>

      <Group title="Strategy" hint="Defaults: preferences soft, exclusions hard.">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium text-muted-foreground">Preferred</p>
          <SevToggle cid="preferred_strategy" {...sp} />
        </div>
        <StrategyChecks selected={preferred} onToggle={(v) => setPreferred(toggle(preferred, v))} idPrefix="pref" />
        <div className="mt-3 flex items-center justify-between">
          <p className="text-xs font-medium text-muted-foreground">Excluded</p>
          <SevToggle cid="excluded_strategy" {...sp} />
        </div>
        <StrategyChecks selected={excluded} onToggle={(v) => setExcluded(toggle(excluded, v))} idPrefix="excl" />
      </Group>

      <Group title="Size & track record">
        <ConstraintField label="Min AUM ($M)" cid="min_aum" {...sp}>
          <Input type="number" value={minAum} onChange={(e) => setMinAum(e.target.value)} placeholder="e.g. 100" />
        </ConstraintField>
        <ConstraintField label="Min track record (months)" cid="min_track_record" {...sp}>
          <Input type="number" value={trackRecord} onChange={(e) => setTrackRecord(e.target.value)} placeholder="e.g. 36" />
        </ConstraintField>
      </Group>

      <Group title="Risk" hint="Evaluated against computed volatility & drawdown.">
        <ConstraintField label="Target volatility (%)" cid="target_volatility" {...sp}>
          <Input type="number" value={targetVol} onChange={(e) => setTargetVol(e.target.value)} placeholder="e.g. 10" />
        </ConstraintField>
        <ConstraintField label="Max drawdown (%)" cid="max_drawdown" {...sp}>
          <Input type="number" value={maxDd} onChange={(e) => setMaxDd(e.target.value)} placeholder="e.g. 20" />
        </ConstraintField>
      </Group>

      <Group title="Label">
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Mandate name (optional)</Label>
          <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. Liquid macro sleeve" />
        </div>
      </Group>
    </div>
  );
}

function Group({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border bg-secondary/40 p-4">
      <h3 className="text-sm font-medium text-brand-green">{title}</h3>
      {hint && <p className="mb-2 text-xs text-muted-foreground">{hint}</p>}
      <div className="mt-2 space-y-3">{children}</div>
    </div>
  );
}

interface SP {
  sev: SevMap;
  pen: PenMap;
  setSev: (cid: string, v: Severity) => void;
  setPen: (cid: string, v: number) => void;
}

function ConstraintField({
  label,
  cid,
  children,
  ...sp
}: { label: string; cid: string; children: React.ReactNode } & SP) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2">
        <Label className="text-xs text-muted-foreground">{label}</Label>
        <SevToggle cid={cid} {...sp} />
      </div>
      {children}
    </div>
  );
}

function SevToggle({ cid, sev, pen, setSev, setPen }: { cid: string } & SP) {
  const s = sev[cid];
  return (
    <div className="flex items-center gap-1.5">
      <div className="inline-flex overflow-hidden rounded border text-[11px] leading-none">
        <button
          type="button"
          onClick={() => setSev(cid, "hard")}
          className={cn("px-1.5 py-1", s === "hard" ? "bg-brand-green text-white" : "text-muted-foreground hover:bg-secondary")}
        >
          Hard
        </button>
        <button
          type="button"
          onClick={() => setSev(cid, "soft")}
          className={cn("px-1.5 py-1", s === "soft" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-secondary")}
        >
          Soft
        </button>
      </div>
      {s === "soft" && (
        <input
          type="number"
          value={pen[cid]}
          onChange={(e) => setPen(cid, Number(e.target.value))}
          title="penalty points if missed"
          className="h-6 w-12 rounded border bg-background px-1 text-[11px] tabular-nums focus:outline-none focus:ring-1 focus:ring-ring"
        />
      )}
    </div>
  );
}

function StrategyChecks({
  selected,
  onToggle,
  idPrefix,
}: {
  selected: string[];
  onToggle: (v: string) => void;
  idPrefix: string;
}) {
  return (
    <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
      {STRATEGY_OPTIONS.map((o) => {
        const id = `${idPrefix}-${o.value}`;
        return (
          <div key={o.value} className="flex items-center gap-2">
            <Checkbox id={id} checked={selected.includes(o.value)} onCheckedChange={() => onToggle(o.value)} />
            <Label htmlFor={id} className="text-xs font-normal text-foreground">{o.label}</Label>
          </div>
        );
      })}
    </div>
  );
}
