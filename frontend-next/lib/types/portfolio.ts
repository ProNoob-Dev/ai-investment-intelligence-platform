export interface Holding {
  ticker: string;
  quantity: number;
  buyPrice: number;
  buyDate?: string;
}

export interface Goal {
  id: string;
  name: string;
  targetAmount: number;
  targetDate: string;
  riskTolerance: string;
  holdings: Holding[];
}

export interface AnalyzedHolding extends Holding {
  currentPrice: number | null;
  invested: number;
  currentValue: number;
  pnl: number;
  pnlPercent: number;
  priceChange: number | null;
  priceChangePercent: number | null;
}

export interface AnalyzedGoal {
  goalId: string;
  goalName: string;
  targetAmount: number;
  targetDate: string;
  riskTolerance: string;
  yearsLeft: number;
  totalInvested: number;
  totalCurrentValue: number;
  totalPnl: number;
  totalPnlPercent: number;
  progress: number;
  holdings: AnalyzedHolding[];
}

export interface RecommendedStock {
  ticker: string;
  quantity: number;
  buyPrice: number;
  reasoning: string;
}

export interface GoalSuggestResponse {
  goalId: string;
  suggestion: string;
  recommendedStocks: RecommendedStock[];
}
