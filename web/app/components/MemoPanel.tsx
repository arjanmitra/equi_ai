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
import { API } from "../constants";
import type { MemoOut } from "../types";
import { MemoReader } from "./MemoReader";

export function MemoPanel({
  runId,
  onCreated,
}: {
  runId: string;
  onCreated?: () => void;
}) {
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
      onCreated?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Memo generation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-brand-green">IC Memo</CardTitle>
        <CardDescription>
          Draft a defendable IC memo — every claim cites a computed metric or
          source field; ungrounded numbers are caught and regenerated.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!memo && (
          <div>
            <Button onClick={generate} disabled={loading}>
              {loading ? "Generating…" : "Generate IC memo"}
            </Button>
            {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
          </div>
        )}
        {memo && <MemoReader memo={memo} />}
      </CardContent>
    </Card>
  );
}
