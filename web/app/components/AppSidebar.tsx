"use client";

import { FileText, SlidersHorizontal } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from "@/components/ui/sidebar";
import type { View } from "../types";

export function AppSidebar({
  view,
  onSelect,
}: {
  view: View;
  onSelect: (kind: "analyses" | "mandates") => void;
}) {
  const onAnalyses = view.kind === "analyses" || view.kind === "analysis";
  const onMandates = view.kind === "mandates" || view.kind === "mandate";

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-center px-1 py-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/equi-white.svg" alt="Equi" className="h-8 w-auto" />
        </div>
      </SidebarHeader>

      <SidebarSeparator />

      <SidebarContent>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton isActive={onAnalyses} onClick={() => onSelect("analyses")}>
              <FileText />
              Analyses
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton isActive={onMandates} onClick={() => onSelect("mandates")}>
              <SlidersHorizontal />
              Mandates
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarContent>

      <SidebarFooter>
        <p className="px-2 text-xs text-sidebar-foreground/40">
          Allocator Memo Builder
        </p>
      </SidebarFooter>
    </Sidebar>
  );
}
