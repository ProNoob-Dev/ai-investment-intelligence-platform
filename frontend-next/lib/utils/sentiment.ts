import type { Recommendation } from "@/lib/types/analysis";

export function sentimentLabel(score: number): string {
  if (score >= 0.2) return "Positive";
  if (score <= -0.2) return "Negative";
  return "Neutral";
}

export function recommendationTone(rec: Recommendation): "buy" | "hold" | "sell" {
  return rec === "BUY" ? "buy" : rec === "SELL" ? "sell" : "hold";
}

export function sentimentColor(score: number): string {
  if (score >= 0.2) return "#0d7480";
  if (score <= -0.2) return "#c2402a";
  return "#8a6d00";
}

export function sentimentPercent(score: number): number {
  return Math.round(((score + 1) / 2) * 100);
}
