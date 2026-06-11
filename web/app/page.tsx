"use client";

import { useCallback, useEffect, useState } from "react";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { API } from "./constants";
import type { MandateOut, MemoSummary, View } from "./types";
import { AppSidebar } from "./components/AppSidebar";
import { MandateView } from "./components/MandateView";
import { MemoView } from "./components/MemoView";
import { Workspace } from "./components/Workspace";

export default function Home() {
  const [memos, setMemos] = useState<MemoSummary[]>([]);
  const [mandates, setMandates] = useState<MandateOut[]>([]);
  const [view, setView] = useState<View>({ kind: "workspace" });

  const refresh = useCallback(async () => {
    try {
      const [m1, m2] = await Promise.all([
        fetch(`${API}/memos`).then((r) => r.json()),
        fetch(`${API}/mandates`).then((r) => r.json()),
      ]);
      setMemos(m1 as MemoSummary[]);
      setMandates(m2 as MandateOut[]);
    } catch {
      /* sidebar lists stay as-is on failure */
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const selectedMandate =
    view.kind === "mandate" ? mandates.find((m) => m.id === view.id) : undefined;

  return (
    <TooltipProvider>
      <SidebarProvider>
        <AppSidebar
          memos={memos}
          mandates={mandates}
          view={view}
          onNewAnalysis={() => setView({ kind: "workspace" })}
          onSelectMemo={(id) => setView({ kind: "memo", id })}
          onSelectMandate={(id) => setView({ kind: "mandate", id })}
        />
        <SidebarInset>
          <div className="mx-auto max-w-5xl px-8 py-10">
            {view.kind === "workspace" && <Workspace onChanged={refresh} />}
            {view.kind === "memo" && <MemoView memoId={view.id} />}
            {view.kind === "mandate" && selectedMandate && (
              <MandateView mandate={selectedMandate} />
            )}
            {view.kind === "mandate" && !selectedMandate && (
              <p className="text-sm text-muted-foreground">Mandate not found.</p>
            )}
          </div>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  );
}
