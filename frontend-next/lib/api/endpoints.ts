import { apiGet, apiPost } from "./client";

import type { AnalysisResult, NewsReference, PeerStock } from "@/lib/types/analysis";
import type {
  OpportunitiesResponse,
  Opportunity,
  ScannerStatus,
} from "@/lib/types/opportunity";
import type { AnalyzedGoal, Goal, GoalSuggestResponse } from "@/lib/types/portfolio";
import type { ChatHistoryResponse, ChatRequest, ChatResponse } from "@/lib/types/chat";

function normalizePeerStock(data: any): PeerStock {
  return {
    ticker: data?.ticker ?? "",
    currentPrice: data?.current_price ?? null,
    priceChange: data?.price_change ?? null,
    priceChangePercent: data?.price_change_percent ?? null,
  };
}

function normalizeNewsReference(data: any): NewsReference {
  return { date: data?.date ?? "", title: data?.title ?? "" };
}

function normalizeAnalysisResult(data: any): AnalysisResult {
  return {
    ticker: data?.ticker ?? "",
    sentiment: data?.sentiment ?? 0,
    nowSentiment: data?.now_sentiment ?? 0,
    patternSentiment: data?.pattern_sentiment ?? 0,
    confidence: data?.confidence ?? 0,
    recentNewsCount: data?.recent_news_count ?? 0,
    patternNewsCount: data?.pattern_news_count ?? 0,
    latestNewsDate: data?.latest_news_date ?? "",
    staleData: data?.stale_data ?? false,
    staleReason: data?.stale_reason ?? "",
    explanation: data?.explanation ?? "",
    positiveDrivers: Array.isArray(data?.positive_drivers) ? data.positive_drivers : [],
    negativeDrivers: Array.isArray(data?.negative_drivers) ? data.negative_drivers : [],
    recommendation: data?.recommendation ?? "HOLD",
    newsReferences: Array.isArray(data?.news_references)
      ? data.news_references.map(normalizeNewsReference)
      : [],
    currentPrice: data?.current_price ?? null,
    priceChange: data?.price_change ?? null,
    priceChangePercent: data?.price_change_percent ?? null,
    aiSummary: data?.ai_summary ?? null,
    peers: Array.isArray(data?.peers) ? data.peers.map(normalizePeerStock) : null,
  };
}

export const analyzeTicker = async (ticker: string): Promise<AnalysisResult> => {
  const data = await apiPost<any>("/analyze", { ticker });
  return normalizeAnalysisResult(data);
};

function normalizeOpportunity(data: any): Opportunity {
  return {
    ticker: data?.ticker ?? "",
    sentiment: data?.sentiment ?? 0,
    newsCount: data?.news_count ?? 0,
    headlines: Array.isArray(data?.headlines) ? data.headlines : [],
    reasoning: data?.reasoning ?? "",
    confidence: data?.confidence ?? 0,
    scanType: data?.scan_type ?? "",
    scannedAt: data?.scanned_at ?? "",
    currentPrice: data?.current_price ?? null,
    priceChange: data?.price_change ?? null,
    priceChangePercent: data?.price_change_percent ?? null,
  };
}

export const getOpportunities = async (): Promise<OpportunitiesResponse> => {
  const data = await apiGet<any>("/opportunities");
  return {
    opportunities: Array.isArray(data?.opportunities)
      ? data.opportunities.map(normalizeOpportunity)
      : [],
    isMarketHours: data?.is_market_hours ?? false,
  };
};

export const getScannerStatus = async (): Promise<ScannerStatus> => {
  const data = await apiGet<any>("/opportunities/status");
  return {
    enabled: data?.enabled ?? false,
    sentimentThreshold: data?.sentiment_threshold ?? 0,
    maxCandidates: data?.max_candidates ?? 0,
    topOpportunities: data?.top_opportunities ?? 0,
    lookbackHours: data?.lookback_hours ?? 0,
    isMarketHours: data?.is_market_hours ?? false,
    shouldRunNow: data?.should_run_now ?? false,
    currentMode: data?.current_mode ?? "",
    opportunitiesCount: data?.opportunities_count ?? 0,
  };
};

export const triggerScan = () =>
  apiPost<{ success: boolean; message: string; opportunities: any[] }>("/opportunities/scan", {});

export const sendChatMessage = (payload: ChatRequest) =>
  apiPost<ChatResponse>("/chat", payload);

export const getChatHistory = (sessionId: string) =>
  apiGet<ChatHistoryResponse>(`/chat/history/${sessionId}`);

export const analyzePortfolio = (goals: Goal[]) =>
  apiPost<{ goals: AnalyzedGoal[]; totalInvested: number; totalCurrentValue: number; totalPnl: number }>(
    "/portfolio/analyze",
    { goals },
  );

export const suggestForGoal = async (goal: Goal): Promise<GoalSuggestResponse> => {
  const data = await apiPost<any>("/portfolio/suggest", { goal });
  return {
    goalId: data?.goalId ?? "",
    suggestion: data?.suggestion ?? "",
    recommendedStocks: Array.isArray(data?.recommended_stocks) ? data.recommended_stocks : [],
  };
};

export const savePortfolio = (userId: string, goals: Goal[]) =>
  apiPost<{ status: string; goal_count: number }>("/storage/portfolio/save", {
    user_id: userId,
    goals,
  });

export const loadPortfolio = (userId: string = "default") =>
  apiGet<{ goals: Goal[]; updated_at: string }>(`/storage/portfolio/load?user_id=${userId}`);

export const saveChatHistory = (sessionId: string, messages: any[]) =>
  apiPost<{ status: string; message_count: number }>("/storage/chat/save", {
    session_id: sessionId,
    messages,
  });

export const loadChatHistory = (sessionId: string) =>
  apiGet<ChatHistoryResponse>(`/storage/chat/load?session_id=${sessionId}`);
