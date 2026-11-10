"use client";

import { useState } from "react";

import { POPULAR_TICKERS } from "@/lib/config";
import { Button } from "@/components/ui/ui";
import { cn } from "@/lib/utils/cn";

export function TickerSearchField({
  onSearch,
  loading,
  initialValue = "",
}: {
  onSearch: (ticker: string) => void;
  loading: boolean;
  initialValue?: string;
}) {
  const [value, setValue] = useState(initialValue);

  const submit = (ticker: string) => {
    const symbol = ticker.trim().toUpperCase();
    if (symbol.length >= 2) onSearch(symbol);
  };

  return (
    <div>
      <form
        className="flex flex-col gap-3 sm:flex-row"
        onSubmit={(e) => {
          e.preventDefault();
          submit(value);
        }}
      >
        <label htmlFor="ticker-search" className="sr-only">
          Stock ticker
        </label>
        <input
          id="ticker-search"
          value={value}
          onChange={(e) => setValue(e.target.value.toUpperCase())}
          placeholder="Type a ticker: RELIANCE, TCS, HDFCBANK"
          autoComplete="off"
          spellCheck={false}
          className="h-12 flex-1 rounded-sm border border-ink/20 bg-white px-4 font-mono text-[15px] tracking-wide placeholder:font-text placeholder:text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        />
        <Button type="submit" disabled={loading} className="sm:w-44">
          {loading ? "Analysing…" : "Analyse stock"}
        </Button>
      </form>
      <div className="mt-4 flex flex-wrap gap-2">
        {POPULAR_TICKERS.slice(0, 12).map((ticker) => (
          <button
            key={ticker}
            type="button"
            onClick={() => {
              setValue(ticker);
              submit(ticker);
            }}
            className={cn(
              "rounded-sm border border-ink/15 bg-white px-3 py-1.5 font-mono text-xs",
              "transition-colors hover:border-accent hover:text-accent",
            )}
          >
            {ticker}
          </button>
        ))}
      </div>
    </div>
  );
}
