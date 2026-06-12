"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { API } from "./constants";
import type { AnalysisOut, MandateOut, View } from "./types";
import { AnalysesTable } from "./components/AnalysesTable";
import { AnalysisDetail } from "./components/AnalysisDetail";
import { AppSidebar } from "./components/AppSidebar";
import { MandatesTable } from "./components/MandatesTable";
import { MandateView } from "./components/MandateView";

export default function Home() {
  const [analyses, setAnalyses] = useState<AnalysisOut[]>([]);
  const [mandates, setMandates] = useState<MandateOut[]>([]);
  const [view, setView] = useState<View>({ kind: "analyses" });

  const refresh = useCallback(async () => {
    try {
      const [a, m] = await Promise.all([
        fetch(`${API}/analyses`).then((r) => r.json()),
        fetch(`${API}/mandates`).then((r) => r.json()),
      ]);
      setAnalyses(a as AnalysisOut[]);
      setMandates(m as MandateOut[]);
    } catch {
      /* keep current lists on failure */
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
        <AppSidebar view={view} onSelect={(kind) => setView({ kind })} />
        <SidebarInset>
          <div className="mx-auto max-w-5xl px-8 py-10">
            {view.kind === "analyses" && (
              <AnalysesTable
                analyses={analyses}
                onChanged={refresh}
                onOpenAnalysis={(id, autoGenerate) => setView({ kind: "analysis", id, autoGenerate })}
              />
            )}

            {view.kind === "mandates" && (
              <MandatesTable
                mandates={mandates}
                onChanged={refresh}
                onOpenMandate={(id) => setView({ kind: "mandate", id })}
              />
            )}

            {view.kind === "analysis" && (
              <AnalysisDetail
                analysisId={view.id}
                autoGenerate={view.autoGenerate}
                onChanged={refresh}
                onBack={() => setView({ kind: "analyses" })}
              />
            )}

            {view.kind === "mandate" && (
              <div className="space-y-4">
                <Button variant="ghost" size="sm" className="-ml-2" onClick={() => setView({ kind: "mandates" })}>
                  <ChevronLeft /> Back to mandates
                </Button>
                {selectedMandate ? (
                  <MandateView mandate={selectedMandate} />
                ) : (
                  <p className="text-sm text-muted-foreground">Mandate not found.</p>
                )}
              </div>
            )}
          </div>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  );
}
