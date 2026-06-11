"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { API } from "../constants";
import type { MemoOut } from "../types";
import { MemoReader } from "./MemoReader";

export function MemoView({ memoId }: { memoId: string }) {
  const [memo, setMemo] = useState<MemoOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setMemo(null);
    setError(null);
    fetch(`${API}/memos/${memoId}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`API ${r.status}`))))
      .then((d) => active && setMemo(d as MemoOut))
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, [memoId]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-brand-green">IC Memo</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          The saved analysis — prose, claim-by-claim citations, and the data
          appendix.
        </p>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {!memo && !error && (
        <Card>
          <CardContent className="space-y-3 pt-6">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-2/3" />
          </CardContent>
        </Card>
      )}

      {memo && (
        <Card>
          <CardContent className="pt-6">
            <MemoReader memo={memo} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
