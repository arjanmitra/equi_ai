"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { API } from "../constants";
import type { MandateOut, MandateSpec } from "../types";
import { MandateFields } from "./MandateFields";

const EMPTY: MandateSpec = { preferred_strategies: [], excluded_strategies: [] };

// Turn FastAPI's 422 body into a readable, field-specific message.
function apiError(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (Array.isArray(detail)) {
    return detail
      .map((e: { loc?: unknown[]; msg?: string }) => {
        const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : "field";
        return `${field}: ${e.msg ?? "invalid"}`;
      })
      .join("; ");
  }
  if (typeof detail === "string") return detail;
  return `Request failed (${status})`;
}

export function MandateModal({
  open,
  onOpenChange,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onSaved: (m: MandateOut) => void;
}) {
  const [spec, setSpec] = useState<MandateSpec>(EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`${API}/mandates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(spec),
      });
      if (!res.ok) {
        throw new Error(apiError(await res.json().catch(() => null), res.status));
      }
      onSaved((await res.json()) as MandateOut);
      onOpenChange(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[88vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>New mandate</DialogTitle>
          <DialogDescription>
            Leave a field blank to skip that check. Hard constraints (liquidity,
            exclusions) eliminate funds; soft ones lower the score.
          </DialogDescription>
        </DialogHeader>

        <MandateFields onChange={setSpec} />

        {error && <p className="text-sm text-destructive">{error}</p>}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={save} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
