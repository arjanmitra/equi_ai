"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { FREQUENCY_OPTIONS, STRATEGY_OPTIONS } from "../constants";
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

  const toggle = (list: string[], v: string) =>
    list.includes(v) ? list.filter((x) => x !== v) : [...list, v];

  function submit() {
    onRun({
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
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-brand-green">Mandate</CardTitle>
        <CardDescription>
          Set the constraints. Leave a field blank to skip that check. Hard
          constraints (liquidity, exclusions) eliminate funds; soft ones (fees,
          preferences, size) lower the score.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Group title="Liquidity (hard)">
          <Field label="Need at least this redemption frequency">
            <Select value={redemption} onValueChange={setRedemption}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="any">Any</SelectItem>
                {FREQUENCY_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field label="Max notice period (days)">
            <Input type="number" value={notice} onChange={(e) => setNotice(e.target.value)} placeholder="e.g. 60" />
          </Field>
          <Field label="Max lockup (months)">
            <Input type="number" value={lockup} onChange={(e) => setLockup(e.target.value)} placeholder="e.g. 12" />
          </Field>
        </Group>

        <Group title="Fees (soft)">
          <Field label="Max management fee (%)">
            <Input type="number" value={mgmtFee} onChange={(e) => setMgmtFee(e.target.value)} placeholder="e.g. 1.8" />
          </Field>
          <Field label="Max performance fee (%)">
            <Input type="number" value={perfFee} onChange={(e) => setPerfFee(e.target.value)} placeholder="e.g. 20" />
          </Field>
        </Group>

        <Group title="Strategy" hint="Exclusions are hard; preferences are soft.">
          <p className="mb-1 text-xs font-medium text-muted-foreground">Preferred</p>
          <StrategyChecks selected={preferred} onToggle={(v) => setPreferred(toggle(preferred, v))} idPrefix="pref" />
          <p className="mb-1 mt-3 text-xs font-medium text-muted-foreground">Excluded</p>
          <StrategyChecks selected={excluded} onToggle={(v) => setExcluded(toggle(excluded, v))} idPrefix="excl" />
        </Group>

        <Group title="Size & track record (soft)">
          <Field label="Min AUM ($M)">
            <Input type="number" value={minAum} onChange={(e) => setMinAum(e.target.value)} placeholder="e.g. 100" />
          </Field>
          <Field label="Min track record (months)">
            <Input type="number" value={trackRecord} onChange={(e) => setTrackRecord(e.target.value)} placeholder="e.g. 36" />
          </Field>
        </Group>

        <Group title="Risk" hint="Evaluated once the metrics stage computes vol & drawdown.">
          <Field label="Target volatility (%)">
            <Input type="number" value={targetVol} onChange={(e) => setTargetVol(e.target.value)} placeholder="e.g. 10" />
          </Field>
          <Field label="Max drawdown (%)">
            <Input type="number" value={maxDd} onChange={(e) => setMaxDd(e.target.value)} placeholder="e.g. 20" />
          </Field>
        </Group>

        <Group title="Label">
          <Field label="Mandate name (optional)">
            <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. Liquid macro sleeve" />
          </Field>
        </Group>
      </CardContent>
      <div className="flex items-center gap-3 px-6 pb-6">
        <Button onClick={submit} disabled={loading}>
          {loading ? "Evaluating…" : "Evaluate funds"}
        </Button>
        {error && <p className="text-sm text-destructive">{error}</p>}
      </div>
    </Card>
  );
}

function Group({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border bg-secondary/40 p-4">
      <h3 className="text-sm font-medium text-brand-green">{title}</h3>
      {hint && <p className="mb-2 text-xs text-muted-foreground">{hint}</p>}
      <div className="mt-2 space-y-3">{children}</div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
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
            <Checkbox
              id={id}
              checked={selected.includes(o.value)}
              onCheckedChange={() => onToggle(o.value)}
            />
            <Label htmlFor={id} className="text-xs font-normal text-foreground">
              {o.label}
            </Label>
          </div>
        );
      })}
    </div>
  );
}
