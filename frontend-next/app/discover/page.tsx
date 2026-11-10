"use client";

import { useCallback, useEffect, useState } from "react";

import { getOpportunities, getScannerStatus, triggerScan } from "@/lib/api/endpoints";
import { OpportunityCard, ScannerStatusCard } from "@/components/discover/DiscoverCards";
import { Card, Skeleton } from "@/components/ui/ui";
import type { Opportunity, ScannerStatus } from "@/lib/types/opportunity";

export default function DiscoverPage() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [status, setStatus] = useState<ScannerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [opps, st] = await Promise.all([getOpportunities(), getScannerStatus()]);
      setOpportunities(opps.opportunities);
      setStatus(st);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load opportunities.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const scan = async () => {
    setScanning(true);
    try {
      await triggerScan();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed.");
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-medium tracking-tight sm:text-4xl">Discover</h1>
      <p className="mt-3 max-w-2xl text-[17px] leading-relaxed text-muted">
        Stocks whose news turned positive in the last 48 hours, picked by the
        scanner, ranked by sentiment, explained by the headlines.
      </p>

      <div className="mt-8">
        {status ? (
          <ScannerStatusCard status={status} onScan={scan} scanning={scanning} />
        ) : (
          <Skeleton className="h-28" />
        )}
      </div>

      {error && (
        <div className="mt-6 rounded-sm border border-[#c2402a]/30 bg-[#c2402a]/[0.05] p-4" role="alert">
          <p className="text-sm text-[#c2402a]">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-56" />
          ))}
        </div>
      ) : opportunities.length > 0 ? (
        <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {opportunities.map((opp) => (
            <OpportunityCard key={opp.ticker} opportunity={opp} />
          ))}
        </div>
      ) : (
        <Card className="mt-6">
          <p className="text-[15px] leading-relaxed text-muted">
            No opportunities on file yet. The scanner runs around market hours
            (8:30–17:00 IST, weekdays). Press “Scan now” to run one immediately.
          </p>
        </Card>
      )}
    </div>
  );
}
