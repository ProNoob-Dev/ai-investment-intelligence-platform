import { create } from "zustand";

import type { AnalysisResult } from "@/lib/types/analysis";

interface AnalysisState {
  result: AnalysisResult | null;
  loading: boolean;
  error: string | null;
  recentTickers: string[];
  setResult: (result: AnalysisResult) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  pushRecent: (ticker: string) => void;
}

export const useAnalysisStore = create<AnalysisState>()((set, get) => ({
  result: null,
  loading: false,
  error: null,
  recentTickers: [],
  setResult: (result) => set({ result, error: null }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  pushRecent: (ticker) => {
    const symbol = ticker.trim().toUpperCase();
    if (!symbol) return;
    set({
      recentTickers: [symbol, ...get().recentTickers.filter((t) => t !== symbol)].slice(0, 10),
    });
  },
}));
