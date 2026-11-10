"use client";

import { AiSummaryCard } from "./AiSummaryCard";
import { DriversCard } from "./DriversCard";
import { NewsCard } from "./NewsCard";
import { PeerComparisonCard } from "./PeerComparisonCard";
import { PriceCard } from "./PriceCard";
import { SentimentCard } from "./SentimentCard";
import { SentimentTrendChart } from "./SentimentTrendChart";
import { Chip } from "@/components/ui/ui";
import type { AnalysisResult } from "@/lib/types/analysis";

export function AnimatedResults({ result }: { result: AnalysisResult }) {
  return (
    <div data-enter className="mt-8">
      {result.staleData && (
        <div className="mb-4 rounded-sm border border-[#8a6d00]/30 bg-[#8a6d00]/[0.06] p-4" role="status">
          <p className="text-sm font-medium text-[#8a6d00]">Stale data</p>
          <p className="mt-1 text-sm leading-relaxed text-muted">{result.staleReason}</p>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Chip tone="accent">{result.ticker}</Chip>
        <Chip tone="neutral">{result.recentNewsCount} recent headlines</Chip>
        <Chip tone="neutral">{result.patternNewsCount} in pattern</Chip>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <PriceCard result={result} />
        <SentimentCard result={result} />
        <div className="lg:col-span-2">
          <AiSummaryCard result={result} />
        </div>
        <DriversCard result={result} />
        <NewsCard result={result} />
        <PeerComparisonCard result={result} />
        <SentimentTrendChart ticker={result.ticker} />
      </div>
    </div>
  );
}
