export interface Opportunity {
  ticker: string;
  sentiment: number;
  newsCount: number;
  headlines: string[];
  reasoning: string;
  confidence: number;
  scanType: string;
  scannedAt: string;
  currentPrice: number | null;
  priceChange: number | null;
  priceChangePercent: number | null;
}

export interface OpportunitiesResponse {
  opportunities: Opportunity[];
  isMarketHours: boolean;
}

export interface ScannerStatus {
  enabled: boolean;
  sentimentThreshold: number;
  maxCandidates: number;
  topOpportunities: number;
  lookbackHours: number;
  isMarketHours: boolean;
  shouldRunNow: boolean;
  currentMode: string;
  opportunitiesCount: number;
}
