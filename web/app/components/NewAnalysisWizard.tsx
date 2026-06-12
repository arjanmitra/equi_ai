"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { API } from "../constants";
import type { MandateOut, RunOut } from "../types";
import { MandateModal } from "./MandateModal";
import { RunResults } from "./RunResults";

const JSON_H = { "Content-Type": "application/json" };

export function NewAnalysisWizard({
  open,
  onOpenChange,
  onComplete,
  onChanged,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onComplete: (analysisId: string) => void;
  onChanged: () => void;
}) {
  const [step, setStep] = useState(1);
  const [universe, setUniverse] = useState<FileList | null>(null);
  const [returns, setReturns] = useState<FileList | null>(null);
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [mandates, setMandates] = useState<MandateOut[]>([]);
  const [mandateId, setMandateId] = useState<string | null>(null);
  const [run, setRun] = useState<RunOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mandateModal, setMandateModal] = useState(false);

  useEffect(() => {
    if (open) loadMandates();
  }, [open]);

  async function loadMandates() {
    try {
      setMandates((await (await fetch(`${API}/mandates`)).json()) as MandateOut[]);
    } catch {
      /* ignore */
    }
  }

  function reset() {
    setStep(1);
    setUniverse(null);
    setReturns(null);
    setUploadId(null);
    setAnalysisId(null);
    setMandateId(null);
    setRun(null);
    setError(null);
  }

  async function cancel() {
    if (analysisId) {
      await fetch(`${API}/analyses/${analysisId}`, { method: "DELETE" }).catch(() => {});
      onChanged();
    }
    reset();
    onOpenChange(false);
  }

  // Step 1: extract universe → ingest returns → compute metrics → create analysis
  async function uploadStep() {
    if (!universe?.length) return;
    setBusy(true);
    setError(null);
    try {
      const uform = new FormData();
      Array.from(universe).forEach((f) => uform.append("files", f));
      const ex = await fetch(`${API}/extract`, { method: "POST", body: uform });
      if (!ex.ok) throw new Error(`extract: ${ex.status}`);
      const { upload_id } = await ex.json();

      if (returns?.length) {
        const rform = new FormData();
        Array.from(returns).forEach((f) => rform.append("files", f));
        const r = await fetch(`${API}/uploads/${upload_id}/returns`, { method: "POST", body: rform });
        if (!r.ok) throw new Error(`returns: ${r.status}`);
      }
      await fetch(`${API}/uploads/${upload_id}/metrics`, { method: "POST", headers: JSON_H, body: "{}" });

      const a = await fetch(`${API}/analyses`, { method: "POST", headers: JSON_H, body: JSON.stringify({ upload_id }) });
      if (!a.ok) throw new Error(`analysis: ${a.status}`);
      setUploadId(upload_id);
      setAnalysisId((await a.json()).id);
      onChanged();
      setStep(2);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  // Step 2: attach mandate → evaluate
  async function evaluateStep() {
    if (!mandateId || !analysisId || !uploadId) return;
    setBusy(true);
    setError(null);
    try {
      await fetch(`${API}/analyses/${analysisId}`, { method: "PATCH", headers: JSON_H, body: JSON.stringify({ mandate_id: mandateId }) });
      const r = await fetch(`${API}/uploads/${uploadId}/runs`, { method: "POST", headers: JSON_H, body: JSON.stringify({ mandate_id: mandateId }) });
      if (!r.ok) throw new Error(`evaluate: ${r.status}`);
      const runOut = (await r.json()) as RunOut;
      await fetch(`${API}/analyses/${analysisId}`, { method: "PATCH", headers: JSON_H, body: JSON.stringify({ run_id: runOut.id }) });
      setRun(runOut);
      setStep(3);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Evaluation failed");
    } finally {
      setBusy(false);
    }
  }

  function generate() {
    if (!analysisId) return;
    const id = analysisId;
    reset();
    onOpenChange(false);
    onChanged();
    onComplete(id); // page routes to the analysis detail, which generates the memo
  }

  const titles = ["Upload data", "Choose a mandate", "Review evaluation"];

  return (
    <>
      <Dialog open={open} onOpenChange={(v) => (v ? onOpenChange(true) : cancel())}>
        <DialogContent className="max-h-[88vh] max-w-3xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>New analysis — step {step} of 3: {titles[step - 1]}</DialogTitle>
            <DialogDescription>
              {step === 1 && "Upload the fund universe and any monthly return files."}
              {step === 2 && "Pick an existing mandate, or create a new one."}
              {step === 3 && "Review the ranked shortlist, then generate the IC memo."}
            </DialogDescription>
          </DialogHeader>

          {step === 1 && (
            <div className="space-y-4">
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Fund universe (CSV / XLSX / HTML / PDF)</Label>
                <Input type="file" multiple accept=".csv,.tsv,.xlsx,.xls,.html,.htm,.pdf" onChange={(e) => setUniverse(e.target.files)} />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Monthly returns (optional)</Label>
                <Input type="file" multiple accept=".csv,.tsv,.xlsx,.xls" onChange={(e) => setReturns(e.target.files)} />
              </div>
              <p className="text-xs text-muted-foreground">
                On Continue, the universe is extracted, returns are ingested, and metrics are computed.
              </p>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-2">
              {mandates.length === 0 && (
                <p className="text-sm text-muted-foreground">No saved mandates yet — create one.</p>
              )}
              {mandates.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setMandateId(m.id)}
                  className={`flex w-full items-center justify-between rounded-md border p-3 text-left text-sm transition-colors ${
                    mandateId === m.id ? "border-primary bg-secondary" : "hover:bg-secondary/50"
                  }`}
                >
                  <span className="font-medium">{m.label ?? `Mandate ${new Date(m.created_at).toLocaleDateString()}`}</span>
                  <span className="text-xs text-muted-foreground">
                    {[m.spec.max_management_fee != null && "fee", m.spec.target_volatility != null && "vol", m.spec.excluded_strategies.length > 0 && "exclusions"].filter(Boolean).join(" · ") || "—"}
                  </span>
                </button>
              ))}
              <Button variant="outline" size="sm" className="mt-2" onClick={() => setMandateModal(true)}>
                <Plus /> Create new mandate
              </Button>
            </div>
          )}

          {step === 3 && run && <RunResults run={run} />}

          {error && <p className="text-sm text-destructive">{error}</p>}

          <DialogFooter>
            <Button variant="outline" onClick={cancel}>Cancel</Button>
            {step === 1 && (
              <Button onClick={uploadStep} disabled={!universe?.length || busy}>
                {busy ? "Processing…" : "Continue"}
              </Button>
            )}
            {step === 2 && (
              <Button onClick={evaluateStep} disabled={!mandateId || busy}>
                {busy ? "Evaluating…" : "Continue"}
              </Button>
            )}
            {step === 3 && <Button onClick={generate}>Generate IC Memo</Button>}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <MandateModal
        open={mandateModal}
        onOpenChange={setMandateModal}
        onSaved={(m) => {
          setMandates((prev) => [m, ...prev]);
          setMandateId(m.id);
          onChanged();
        }}
      />
    </>
  );
}
