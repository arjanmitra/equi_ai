"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { AnalysisOut } from "../types";
import { NewAnalysisWizard } from "./NewAnalysisWizard";

export function AnalysesTable({
  analyses,
  onOpenAnalysis,
  onChanged,
}: {
  analyses: AnalysisOut[];
  onOpenAnalysis: (id: string, autoGenerate?: boolean) => void;
  onChanged: () => void;
}) {
  const [wizard, setWizard] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-brand-green">Analyses</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Every analysis you&apos;ve run — click a row to open it.
          </p>
        </div>
        <Button onClick={() => setWizard(true)}>
          <Plus /> New analysis
        </Button>
      </div>

      <Card>
        <CardContent className="pt-6">
          {analyses.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">
              No analyses yet. Click “New analysis” to start.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Universe file</TableHead>
                  <TableHead>Returns files</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Memo</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {analyses.map((a) => (
                  <TableRow
                    key={a.id}
                    className="cursor-pointer"
                    onClick={() => onOpenAnalysis(a.id)}
                  >
                    <TableCell className="font-mono text-xs">{a.id.slice(0, 8)}</TableCell>
                    <TableCell>{a.universe_files.join(", ") || "—"}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {a.returns_files.join(", ") || "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(a.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      {a.has_memo ? (
                        <Badge variant="success">memo</Badge>
                      ) : (
                        <Badge variant="secondary">none</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <NewAnalysisWizard
        open={wizard}
        onOpenChange={setWizard}
        onChanged={onChanged}
        onComplete={(id) => onOpenAnalysis(id, true)}
      />
    </div>
  );
}
