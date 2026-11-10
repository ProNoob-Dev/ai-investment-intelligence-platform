"use client";

import Link from "next/link";

import { Card, Chip } from "@/components/ui/ui";
import { formatINR, formatPercent, timeAgo } from "@/lib/utils/format";
import { sentimentColor } from "@/lib/utils/sentiment";
import type { Opportunity } from "@/lib/types/opportunity";

export function OpportunityCard({ opportunity }: { opportunity: Opportunity }) {
  const score = opportunity.sentiment;
  const angle = -90 + ((score + 1) / 2) * 180;
  return (
    <Link href={`/analyze?ticker=${opportunity.ticker}`} className="block" data-ui>
      <Card className="lift h-full p-4 sm:p-5" dataUi>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="font-mono text-lg font-medium">{opportunity.ticker}</p>
            <p className="mt-0.5 font-mono text-xs text-muted">
              {opportunity.newsCount} {opportunity.newsCount === 1 ? "article" : "articles"} · {timeAgo(opportunity.scannedAt)}
            </p>
          </div>
          <Chip tone={opportunity.sentiment >= 0.2 ? "buy" : "neutral"}>
            {opportunity.sentiment.toFixed(2)}
          </Chip>
        </div>
        <p className="mt-3 line-clamp-3 text-sm leading-relaxed sm:line-clamp-none">{opportunity.reasoning}</p>
        <div className="mt-4" aria-label={`Sentiment ${opportunity.sentiment.toFixed(2)} on a scale from −1 to +1`}>
          <svg viewBox="0 0 200 24" className="h-6 w-full" role="img" aria-hidden>
            <rect x="0" y="0" width="80" height="24" fill="#c2402a" opacity="0.6" />
            <rect x="80" y="0" width="40" height="24" fill="#8a6d00" opacity="0.5" />
            <rect x="120" y="0" width="80" height="24" fill="#0d7480" opacity="0.6" />
            <line x1={((score + 1) / 2) * 200} y1="0" x2={((score + 1) / 2) * 200} y2="24" stroke="#1f3038" strokeWidth="3" />
          </svg>
          <div className="mt-1.5 flex justify-between font-mono text-[11px] text-muted">
            <span>−1</span>
            <span>sentiment {opportunity.sentiment.toFixed(2)}</span>
            <span>+1</span>
          </div>
        </div>
        {opportunity.headlines.length > 0 && (
          <p className="mt-3 hidden border-t border-ink/10 pt-3 text-[13px] leading-relaxed text-muted sm:block">
            {opportunity.headlines[0]}
          </p>
        )}
        <div className="mt-3 hidden items-center justify-between font-mono text-sm sm:flex">
          <span>{formatINR(opportunity.currentPrice)}</span>
          <span style={{ color: sentimentColor(opportunity.sentiment) }}>
            {formatPercent(opportunity.priceChangePercent)}
          </span>
          <span className="text-muted">confidence {Math.round(opportunity.confidence * 100)}%</span>
        </div>
      </Card>
    </Link>
  );
}

export function ScannerStatusCard({
  status,
  onScan,
  scanning,
}: {
  status: {
    enabled: boolean;
    isMarketHours: boolean;
    shouldRunNow: boolean;
    currentMode: string;
    opportunitiesCount: number;
    sentimentThreshold: number;
    lookbackHours: number;
  };
  onScan: () => void;
  scanning: boolean;
}) {
  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-muted">Scanner</p>
          <p className="mt-2 font-display text-xl font-medium">
            {status.isMarketHours ? "Market is open" : "Market is closed"}
            <span className="ml-2 text-sm font-normal text-muted">
              · {status.currentMode.replace("_", " ")}
            </span>
          </p>
          <p className="mt-1 text-sm text-muted">
            {status.opportunitiesCount} opportunities on file · sentiment above{" "}
            {status.sentimentThreshold} · last {status.lookbackHours}h of news
          </p>
        </div>
        <button
          type="button"
          onClick={onScan}
          disabled={scanning || !status.enabled}
          className="btn-step inline-flex h-12 items-center justify-center rounded-sm bg-accent px-6 text-[15px] font-medium text-white hover:bg-[#0a5e68] disabled:opacity-50"
        >
          {scanning ? "Scanning…" : "Scan now"}
        </button>
      </div>
    </Card>
  );
}
