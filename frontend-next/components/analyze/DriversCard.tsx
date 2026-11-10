"use client";

import { Card } from "@/components/ui/ui";
import { sentimentColor } from "@/lib/utils/sentiment";
import type { AnalysisResult } from "@/lib/types/analysis";

export function DriversCard({ result }: { result: AnalysisResult }) {
  const hasDrivers = result.positiveDrivers.length > 0 || result.negativeDrivers.length > 0;
  return (
    <Card>
      <h3 className="font-display text-lg font-medium">What is driving it</h3>
      {!hasDrivers && (
        <p className="mt-3 text-sm text-muted">
          No clear drivers in the headlines we matched. The sentiment comes from the
          overall tone of the coverage.
        </p>
      )}
      {result.positiveDrivers.length > 0 && (
        <div className="mt-4">
          <p className="font-mono text-[11px] uppercase tracking-wider text-accent">Pushing up</p>
          <ul className="mt-2 space-y-2">
            {result.positiveDrivers.map((driver) => (
              <li key={driver} className="flex gap-2 text-sm leading-relaxed">
                <span aria-hidden className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-accent" />
                {driver}
              </li>
            ))}
          </ul>
        </div>
      )}
      {result.negativeDrivers.length > 0 && (
        <div className="mt-4">
          <p className="font-mono text-[11px] uppercase tracking-wider text-[#c2402a]">Pulling down</p>
          <ul className="mt-2 space-y-2">
            {result.negativeDrivers.map((driver) => (
              <li key={driver} className="flex gap-2 text-sm leading-relaxed">
                <span aria-hidden className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-[#c2402a]" />
                {driver}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
