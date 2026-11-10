"use client";

import type { CSSProperties } from "react";

import { Card } from "@/components/ui/ui";
import { cn } from "@/lib/utils/cn";
import { sentimentColor, sentimentLabel, sentimentPercent } from "@/lib/utils/sentiment";
import type { AnalysisResult } from "@/lib/types/analysis";

/** Half-donut gauge: -1 (left) to +1 (right), needle at the sentiment. */
export function SentimentCard({ result, compact = false }: { result: AnalysisResult; compact?: boolean }) {
  const score = result.sentiment;
  const angle = -90 + ((score + 1) / 2) * 180;
  const color = sentimentColor(score);
  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-muted">News sentiment</p>
          <p className="mt-2 font-display text-[28px] font-medium tracking-tight sm:text-4xl">
            {score.toFixed(2)}
            <span className="ml-2 text-lg text-muted">{sentimentLabel(score)}</span>
          </p>
        </div>
        <span className="font-mono text-xs text-muted">
          {sentimentPercent(score)} / 100
        </span>
      </div>

      <svg viewBox="0 0 200 110" className={cn("mx-auto mt-2 w-full", compact ? "max-w-[180px] sm:max-w-[320px]" : "max-w-[320px]")} role="img"
        aria-label={`Sentiment gauge: ${score.toFixed(2)}, ${sentimentLabel(score)}`}>
        <path d="M 10 100 A 90 90 0 0 1 190 100" fill="none" stroke="#ecf0f2" strokeWidth="14" />
        <path d="M 10 100 A 90 90 0 0 1 100 10" fill="none" stroke="#c2402a" strokeWidth="14" opacity="0.55" />
        <path d="M 100 10 A 90 90 0 0 1 190 100" fill="none" stroke="#0d7480" strokeWidth="14" opacity="0.55" />
        <g className="gauge-needle" style={{ "--needle": `${angle}deg` } as CSSProperties}>
          <line x1="100" y1="100" x2="100" y2="26" stroke={color} strokeWidth="3" strokeLinecap="round" />
          <circle cx="100" cy="100" r="6" fill={color} />
        </g>
        <text x="10" y="110" fontSize="10" fill="#5d6b72" textAnchor="start">−1</text>
        <text x="100" y="110" fontSize="10" fill="#5d6b72" textAnchor="middle">0</text>
        <text x="190" y="110" fontSize="10" fill="#5d6b72" textAnchor="end">+1</text>
      </svg>

      {!compact && (
        <>
          {/* Bleeds to the card's edges so the row spans the column's lines. */}
          <dl className="-mx-5 mt-2 grid grid-cols-3 gap-3 border-t border-ink/10 px-5 pt-4 text-center">
            <div>
              <dt className="font-mono text-[11px] uppercase tracking-wider text-muted">Now</dt>
              <dd className="mt-1 font-mono text-lg">{result.nowSentiment.toFixed(2)}</dd>
            </div>
            <div>
              <dt className="font-mono text-[11px] uppercase tracking-wider text-muted">Pattern</dt>
              <dd className="mt-1 font-mono text-lg">{result.patternSentiment.toFixed(2)}</dd>
            </div>
            <div>
              <dt className="font-mono text-[11px] uppercase tracking-wider text-muted">Confidence</dt>
              <dd className="mt-1 font-mono text-lg">{Math.round(result.confidence * 100)}%</dd>
            </div>
          </dl>
          <p className="mt-4 line-clamp-2 text-sm leading-relaxed text-muted">{result.explanation}</p>
        </>
      )}
    </Card>
  );
}
