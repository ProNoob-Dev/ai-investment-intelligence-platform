import { create } from "zustand";
import { persist } from "zustand/middleware";

import { CONFIG } from "@/lib/config";

interface WatchlistState {
  tickers: string[];
  addTicker: (ticker: string) => void;
  removeTicker: (ticker: string) => void;
  isWatched: (ticker: string) => boolean;
}

export const useWatchlistStore = create<WatchlistState>()(
  persist(
    (set, get) => ({
      tickers: ["RELIANCE", "TCS", "HDFCBANK", "INFY"],
      addTicker: (ticker) => {
        const symbol = ticker.trim().toUpperCase();
        if (!symbol || get().tickers.includes(symbol)) return;
        set({ tickers: [symbol, ...get().tickers].slice(0, CONFIG.MAX_WATCHLIST_TICKERS) });
      },
      removeTicker: (ticker) =>
        set({ tickers: get().tickers.filter((t) => t !== ticker.toUpperCase()) }),
      isWatched: (ticker) => get().tickers.includes(ticker.toUpperCase()),
    }),
    { name: "aiip-watchlist" },
  ),
);

interface TrendEntry {
  ticker: string;
  sentiment: number;
  at: string;
}

interface TrendState {
  entries: TrendEntry[];
  push: (entry: TrendEntry) => void;
}

export const useTrendStore = create<TrendState>()(
  persist(
    (set, get) => ({
      entries: [],
      push: (entry) =>
        set({
          entries: [entry, ...get().entries.filter((e) => e.ticker !== entry.ticker)]
            .slice(0, CONFIG.MAX_TREND_ENTRIES),
        }),
    }),
    { name: "aiip-trend" },
  ),
);
