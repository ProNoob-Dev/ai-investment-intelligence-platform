"use client";

import { useState } from "react";

import { Button, Card, Chip } from "@/components/ui/ui";
import { formatCompactINR, formatINR, formatPercent, formatSignedINR } from "@/lib/utils/format";
import type { AnalyzedGoal, Goal, RecommendedStock } from "@/lib/types/portfolio";

export function GoalCard({
  goal,
  onSuggest,
  onAddHolding,
  suggestion,
  suggesting,
}: {
  goal: AnalyzedGoal;
  onSuggest: (goal: Goal) => void;
  onAddHolding: (goalId: string) => void;
  suggestion?: { suggestion: string; recommendedStocks: RecommendedStock[] } | null;
  suggesting: boolean;
}) {
  const [showSuggestion, setShowSuggestion] = useState(false);
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-display text-xl font-medium">{goal.goalName}</h3>
          <p className="mt-1 font-mono text-xs text-muted">
            Target {formatCompactINR(goal.targetAmount)} · {goal.yearsLeft}y left · {goal.riskTolerance}
          </p>
        </div>
        <Chip tone="accent">{goal.progress}%</Chip>
      </div>

      <div className="mt-4 h-2 w-full overflow-hidden rounded-sm bg-surface" role="progressbar"
        aria-valuenow={goal.progress} aria-valuemin={0} aria-valuemax={100}
        aria-label={`Progress towards ${goal.goalName}`}>
        <div className="h-full bg-accent" style={{ width: `${goal.progress}%` }} />
      </div>

      <dl className="mt-4 grid grid-cols-3 gap-3 text-center">
        <div>
          <dt className="font-mono text-[11px] uppercase tracking-wider text-muted">Invested</dt>
          <dd className="mt-1 font-mono text-sm">{formatCompactINR(goal.totalInvested)}</dd>
        </div>
        <div>
          <dt className="font-mono text-[11px] uppercase tracking-wider text-muted">Value</dt>
          <dd className="mt-1 font-mono text-sm">{formatCompactINR(goal.totalCurrentValue)}</dd>
        </div>
        <div>
          <dt className="font-mono text-[11px] uppercase tracking-wider text-muted">P&amp;L</dt>
          <dd className={`mt-1 font-mono text-sm ${goal.totalPnl >= 0 ? "text-accent" : "text-[#c2402a]"}`}>
            {formatSignedINR(goal.totalPnl)}
          </dd>
        </div>
      </dl>

      {goal.holdings.length > 0 ? (
        <ul className="mt-4 divide-y divide-ink/10">
          {goal.holdings.map((h) => (
            <li key={h.ticker} className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
              <span className="font-mono text-sm">{h.ticker}</span>
              <span className="font-mono text-xs text-muted">
                {h.quantity} × {formatINR(h.buyPrice)}
              </span>
              <span className="font-mono text-sm">{formatINR(h.currentValue)}</span>
              <span className={`font-mono text-sm ${h.pnl >= 0 ? "text-accent" : "text-[#c2402a]"}`}>
                {formatPercent(h.pnlPercent)}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-sm text-muted">No holdings yet. Add your first stock below.</p>
      )}

      <div className="mt-5 flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => onAddHolding(goal.goalId)} className="h-10 px-4 text-sm">
          Add holding
        </Button>
        <Button
          variant="ghost"
          onClick={() => {
            onSuggest({
              id: goal.goalId, name: goal.goalName, targetAmount: goal.targetAmount,
              targetDate: goal.targetDate, riskTolerance: goal.riskTolerance,
              holdings: goal.holdings.map((h) => ({
                ticker: h.ticker, quantity: h.quantity, buyPrice: h.buyPrice,
              })),
            });
            setShowSuggestion(true);
          }}
          disabled={suggesting}
          className="h-10 px-4 text-sm"
        >
          {suggesting ? "Thinking…" : "Get AI suggestions"}
        </Button>
      </div>

      {showSuggestion && suggestion && (
        <div className="mt-4 rounded-sm border border-accent/30 bg-accent/[0.04] p-4">
          <p className="text-sm leading-relaxed whitespace-pre-line">{suggestion.suggestion}</p>
          {suggestion.recommendedStocks.length > 0 && (
            <ul className="mt-3 space-y-2">
              {suggestion.recommendedStocks.map((s) => (
                <li key={s.ticker} className="text-sm">
                  <span className="font-mono font-medium">{s.ticker}</span>
                  {" — "}
                  {s.quantity} × {formatINR(s.buyPrice)}
                  <span className="text-muted"> · {s.reasoning}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  );
}

export function PortfolioEmptyState({ onAddGoal }: { onAddGoal: () => void }) {
  return (
    <Card className="py-12 text-center">
      <p className="font-display text-xl font-medium">No goals yet</p>
      <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-muted">
        Set a goal: a house deposit, a child’s education, retirement. Add the
        stocks you hold for it, and the platform tracks P&amp;L and progress for you.
      </p>
      <Button onClick={onAddGoal} className="mt-6">
        Create your first goal
      </Button>
    </Card>
  );
}
