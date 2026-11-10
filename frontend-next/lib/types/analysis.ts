export interface PeerStock {
  ticker: string;
  currentPrice: number | null;
  priceChange: number | null;
  priceChangePercent: number | null;
}

export interface NewsReference {
  date: string;
  title: string;
}

export type Recommendation = "BUY" | "HOLD" | "SELL";

export interface AnalysisResult {
  ticker: string;
  sentiment: number;
  nowSentiment: number;
  patternSentiment: number;
  confidence: number;
  recentNewsCount: number;
  patternNewsCount: number;
  latestNewsDate: string;
  staleData: boolean;
  staleReason: string;
  explanation: string;
  positiveDrivers: string[];
  negativeDrivers: string[];
  recommendation: Recommendation;
  newsReferences: NewsReference[];
  currentPrice: number | null;
  priceChange: number | null;
  priceChangePercent: number | null;
  aiSummary: string | null;
  peers: PeerStock[] | null;
}
