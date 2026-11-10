"use client";

import { Suspense, useCallback, useEffect } from "react";
import { useSearchParams } from "next/navigation";

import { analyzeTicker } from "@/lib/api/endpoints";
import { useAnalysisStore } from "@/lib/hooks/useAnalysisStore";
import { useTrendStore, useWatchlistStore } from "@/lib/hooks/useStores";
import { AnimatedResults } from "@/components/analyze/AnimatedResults";
import { AnalysisSkeleton, ErrorDisplay } from "@/components/analyze/AnalysisState";
import { TickerSearchField } from "@/components/analyze/TickerSearchField";
import { Chip } from "@/components/ui/ui";

function AnalyzeContent() {
  const searchParams = useSearchParams();
  const { result, loading, error, setResult, setLoading, setError, pushRecent, recentTickers } =
    useAnalysisStore();
  const pushTrend = useTrendStore((s) => s.push);
  const { tickers: watchlist, addTicker, removeTicker, isWatched } = useWatchlistStore();

  const run = useCallback(
    async (ticker: string) => {
      const symbol = ticker.trim().toUpperCase();
      if (!symbol) return;
      setLoading(true);
      setError(null);
      try {
        const data = await analyzeTicker(symbol);
        setResult(data);
        pushRecent(symbol);
        pushTrend({ ticker: symbol, sentiment: data.sentiment, at: new Date().toISOString() });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Analysis failed. Is the API running?");
      } finally {
        setLoading(false);
      }
    },
    [setLoading, setError, setResult, pushRecent, pushTrend],
  );

  useEffect(() => {
    const ticker = searchParams.get("ticker");
    if (ticker) run(ticker);
    // Run once per ticker param; run is stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-medium tracking-tight sm:text-4xl">Analyse a stock</h1>
      <p className="mt-3 max-w-2xl text-[17px] leading-relaxed text-muted">
        News sentiment, live price, peers and an AI summary, for any NSE or BSE stock.
      </p>

      <div className="mt-8">
        <TickerSearchField onSearch={run} loading={loading} initialValue={result?.ticker ?? ""} />
      </div>

      {recentTickers.length > 0 && (
        <div className="mt-6 flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-muted">Recent:</span>
          {recentTickers.map((t) => (
            <button key={t} type="button" onClick={() => run(t)}
              className="link-underline font-mono text-sm text-accent">
              {t}
            </button>
          ))}
        </div>
      )}

      {result && (
        <div className="mt-6 flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-muted">Watchlist:</span>
          {watchlist.map((t) => (
            <Chip key={t} tone={t === result.ticker ? "accent" : "neutral"}>
              <button type="button" onClick={() => run(t)}>{t}</button>
            </Chip>
          ))}
          <button
            type="button"
            onClick={() =>
              isWatched(result.ticker) ? removeTicker(result.ticker) : addTicker(result.ticker)
            }
            className="link-underline text-sm font-medium text-accent"
          >
            {isWatched(result.ticker) ? `Remove ${result.ticker} from watchlist` : `Watch ${result.ticker}`}
          </button>
        </div>
      )}

      {loading && <AnalysisSkeleton />}
      {error && !loading && <ErrorDisplay message={error} onRetry={() => result && run(result.ticker)} />}
      {result && !loading && <AnimatedResults result={result} />}
      {!result && !loading && !error && (
        <p className="mt-10 text-[15px] leading-relaxed text-muted">
          Try RELIANCE, TCS or HDFCBANK, or any ticker you hold.
        </p>
      )}
    </div>
  );
}

export default function AnalyzePage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">Loading…</div>}>
      <AnalyzeContent />
    </Suspense>
  );
}
