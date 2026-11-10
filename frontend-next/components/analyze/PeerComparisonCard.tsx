"use client";

import { Card } from "@/components/ui/ui";
import { formatINR, formatPercent } from "@/lib/utils/format";
import type { AnalysisResult } from "@/lib/types/analysis";

export function PeerComparisonCard({ result }: { result: AnalysisResult }) {
  const peers = result.peers ?? [];
  if (peers.length === 0) return null;
  return (
    <Card>
      <h3 className="font-display text-lg font-medium">Peers</h3>
      <ul className="mt-4 space-y-3">
        {peers.map((peer) => (
          <li key={peer.ticker} className="flex items-center justify-between gap-4">
            <span className="font-mono text-sm">{peer.ticker}</span>
            <span className="font-mono text-sm">{formatINR(peer.currentPrice)}</span>
            <span
              className={
                peer.priceChangePercent === null
                  ? "font-mono text-sm text-muted"
                  : peer.priceChangePercent >= 0
                    ? "font-mono text-sm text-accent"
                    : "font-mono text-sm text-[#c2402a]"
              }
            >
              {formatPercent(peer.priceChangePercent)}
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
