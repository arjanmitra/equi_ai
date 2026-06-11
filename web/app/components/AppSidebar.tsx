"use client";

import { CheckCircle2, FileText, Plus, SlidersHorizontal } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from "@/components/ui/sidebar";
import type { MandateOut, MemoSummary, View } from "../types";

export function AppSidebar({
  memos,
  mandates,
  view,
  onNewAnalysis,
  onSelectMemo,
  onSelectMandate,
}: {
  memos: MemoSummary[];
  mandates: MandateOut[];
  view: View;
  onNewAnalysis: () => void;
  onSelectMemo: (id: string) => void;
  onSelectMandate: (id: string) => void;
}) {
  const fmtDate = (s: string) => new Date(s).toLocaleDateString();

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-center px-1 py-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/equi-white.svg" alt="Equi" className="h-8 w-auto" />
        </div>
        <SidebarMenuButton
          onClick={onNewAnalysis}
          className="bg-primary font-medium text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground"
        >
          <Plus />
          New analysis
        </SidebarMenuButton>
      </SidebarHeader>

      <SidebarSeparator />

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Memos</SidebarGroupLabel>
          <SidebarMenu>
            {memos.length === 0 && (
              <p className="px-2 py-1 text-xs text-sidebar-foreground/40">
                No memos yet
              </p>
            )}
            {memos.map((m) => (
              <SidebarMenuItem key={m.id}>
                <SidebarMenuButton
                  isActive={view.kind === "memo" && view.id === m.id}
                  onClick={() => onSelectMemo(m.id)}
                >
                  <FileText />
                  <span className="flex-1 truncate">
                    {m.label ?? `Memo ${fmtDate(m.created_at)}`}
                  </span>
                  {m.all_verified && (
                    <CheckCircle2 className="text-sidebar-primary" />
                  )}
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Mandates</SidebarGroupLabel>
          <SidebarMenu>
            {mandates.length === 0 && (
              <p className="px-2 py-1 text-xs text-sidebar-foreground/40">
                No mandates yet
              </p>
            )}
            {mandates.map((m) => (
              <SidebarMenuItem key={m.id}>
                <SidebarMenuButton
                  isActive={view.kind === "mandate" && view.id === m.id}
                  onClick={() => onSelectMandate(m.id)}
                >
                  <SlidersHorizontal />
                  <span className="flex-1 truncate">
                    {m.label ?? `Mandate ${fmtDate(m.created_at)}`}
                  </span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <p className="px-2 text-xs text-sidebar-foreground/40">
          Allocator Memo Builder
        </p>
      </SidebarFooter>
    </Sidebar>
  );
}
