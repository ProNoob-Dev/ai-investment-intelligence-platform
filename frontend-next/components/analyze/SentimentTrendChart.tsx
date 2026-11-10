"use client";

import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card } from "@/components/ui/ui";
import { useTrendStore } from "@/lib/hooks/useStores";
import { sentimentColor } from "@/lib/utils/sentiment";

export function SentimentTrendChart({ ticker }: { ticker: string }) {
  const entries = useTrendStore((s) => s.entries);
  const data = useMemo(
    () =>
      entries
        .filter((e) => e.ticker === ticker)
        .slice(0, 10)
        .reverse()
        .map((e, i) => ({
          label: `#${i + 1}`,
          sentiment: Number(e.sentiment.toFixed(2)),
          at: e.at,
        })),
    [entries, ticker],
  );
  if (data.length < 2) return null;
  return (
    <Card>
      <h3 className="font-display text-lg font-medium">Sentiment over your checks</h3>
      <p className="mt-1 text-sm text-muted">
        Each point is the score from one analysis of {ticker} in this browser.
      </p>
      <div className="mt-4 h-48 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
            <CartesianGrid stroke="#ecf0f2" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#5d6b72" }} axisLine={false} tickLine={false} />
            <YAxis domain={[-1, 1]} tick={{ fontSize: 11, fill: "#5d6b72" }} axisLine={false} tickLine={false} />
            <Tooltip
              formatter={(value) => [`${Number(value).toFixed(2)}`, "Sentiment"]}
              labelFormatter={(_, payload) => payload?.[0]?.payload?.at ?? ""}
              contentStyle={{ borderRadius: 2, border: "1px solid #ecf0f2", fontSize: 13 }}
            />
            <ReferenceLine y={0} stroke="#5d6b72" strokeDasharray="3 3" />
            <ReferenceLine y={0.2} stroke="#0d7480" strokeDasharray="3 3" />
            <ReferenceLine y={-0.2} stroke="#c2402a" strokeDasharray="3 3" />
            <Line
              type="monotone"
              dataKey="sentiment"
              stroke={sentimentColor(data[data.length - 1].sentiment)}
              strokeWidth={2}
              dot={{ r: 3, fill: "#1f3038" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
