"use client";

import { Card, Chip } from "@/components/ui/ui";
import { formatINR, formatPercent, formatSignedINR } from "@/lib/utils/format";
import { recommendationTone } from "@/lib/utils/sentiment";
import { cn } from "@/lib/utils/cn";
import type { AnalysisResult } from "@/lib/types/analysis";

export function PriceCard({ result }: { result: AnalysisResult }) {
  const change = result.priceChange ?? null;
  const changePct = result.priceChangePercent ?? null;
  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-muted">Live price</p>
          <p className="mt-2 font-display text-[28px] font-medium tracking-tight sm:text-4xl">
            {formatINR(result.currentPrice)}
          </p>
          <p className={cn("mt-1 font-mono text-sm",
            change === null ? "text-muted" : change >= 0 ? "text-accent" : "text-[#c2402a]")}>
            {change !== null ? (
              <>
                {formatSignedINR(change)} ({formatPercent(changePct)})
                <span className="text-muted"> today</span>
              </>
            ) : (
              "Price unavailable right now"
            )}
          </p>
        </div>
        <Chip tone={recommendationTone(result.recommendation)}>{result.recommendation}</Chip>
      </div>
      <p className="mt-4 text-sm leading-relaxed text-muted">
        {result.ticker} on NSE. Price from Yahoo Finance, refreshed every five minutes.
      </p>
    </Card>
  );
}
