"use client";

import { Card } from "@/components/ui/ui";
import type { AnalysisResult } from "@/lib/types/analysis";

export function AiSummaryCard({ result }: { result: AnalysisResult }) {
  if (!result.aiSummary) return null;
  return (
    <Card className="border-accent/30 bg-accent/[0.04]">
      <p className="font-mono text-xs uppercase tracking-widest text-accent">AI summary</p>
      <p className="mt-3 text-[15px] leading-relaxed">{result.aiSummary}</p>
    </Card>
  );
}
