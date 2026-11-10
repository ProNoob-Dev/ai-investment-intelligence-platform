"use client";

import { Card } from "@/components/ui/ui";
import { timeAgo } from "@/lib/utils/format";
import type { AnalysisResult } from "@/lib/types/analysis";

export function NewsCard({ result }: { result: AnalysisResult }) {
  return (
    <Card>
      <div className="flex items-baseline justify-between gap-4">
        <h3 className="font-display text-lg font-medium">News behind the call</h3>
        <span className="font-mono text-xs text-muted">
          {result.recentNewsCount} recent · {result.patternNewsCount} total
        </span>
      </div>
      {result.newsReferences.length === 0 ? (
        <p className="mt-3 text-sm text-muted">
          No matched headlines for this ticker yet. Try a larger stock, or check back
          after the next news ingest.
        </p>
      ) : (
        <ul className="mt-4 divide-y divide-ink/10">
          {result.newsReferences.map((ref, i) => (
            <li key={`${ref.title}-${i}`} className="flex items-baseline justify-between gap-4 py-3 first:pt-0 last:pb-0">
              <span className="text-sm leading-relaxed">{ref.title}</span>
              <span className="shrink-0 font-mono text-xs text-muted">{timeAgo(ref.date)}</span>
            </li>
          ))}
        </ul>
      )}
      {result.latestNewsDate && (
        <p className="mt-4 border-t border-ink/10 pt-3 font-mono text-xs text-muted">
          Latest matched headline: {timeAgo(result.latestNewsDate)}
        </p>
      )}
    </Card>
  );
}
