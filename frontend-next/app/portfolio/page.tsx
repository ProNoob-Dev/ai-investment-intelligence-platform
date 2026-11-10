"use client";

import { useCallback, useEffect, useState } from "react";

import {
  analyzePortfolio,
  loadPortfolio,
  savePortfolio,
  suggestForGoal,
} from "@/lib/api/endpoints";
import { Button, Card, Skeleton } from "@/components/ui/ui";
import { GoalCard, PortfolioEmptyState } from "@/components/portfolio/PortfolioCards";
import { formatCompactINR } from "@/lib/utils/format";
import type {
  AnalyzedGoal,
  Goal,
  GoalSuggestResponse,
  Holding,
} from "@/lib/types/portfolio";

const USER_ID = "default";

function GoalForm({
  onSave,
  onCancel,
}: {
  onSave: (goal: Goal) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [targetAmount, setTargetAmount] = useState("");
  const [targetDate, setTargetDate] = useState("2030-01-01");
  const [riskTolerance, setRiskTolerance] = useState("moderate");
  return (
    <Card>
      <h3 className="font-display text-lg font-medium">New goal</h3>
      <form
        className="mt-4 grid gap-3 sm:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (!name.trim() || !targetAmount) return;
          onSave({
            id: `goal-${Date.now()}`,
            name: name.trim(),
            targetAmount: Number(targetAmount),
            targetDate,
            riskTolerance,
            holdings: [],
          });
        }}
      >
        <label className="block">
          <span className="font-mono text-xs text-muted">Goal name</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required
            placeholder="Retirement" className="mt-1 h-11 w-full rounded-sm border border-ink/20 bg-white px-3 focus:border-accent focus:outline-none" />
        </label>
        <label className="block">
          <span className="font-mono text-xs text-muted">Target amount (₹)</span>
          <input value={targetAmount} onChange={(e) => setTargetAmount(e.target.value)} required
            inputMode="decimal" placeholder="1000000" className="mt-1 h-11 w-full rounded-sm border border-ink/20 bg-white px-3 focus:border-accent focus:outline-none" />
        </label>
        <label className="block">
          <span className="font-mono text-xs text-muted">Target date</span>
          <input type="date" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} required
            className="mt-1 h-11 w-full rounded-sm border border-ink/20 bg-white px-3 focus:border-accent focus:outline-none" />
        </label>
        <label className="block">
          <span className="font-mono text-xs text-muted">Risk tolerance</span>
          <select value={riskTolerance} onChange={(e) => setRiskTolerance(e.target.value)}
            className="mt-1 h-11 w-full rounded-sm border border-ink/20 bg-white px-3 focus:border-accent focus:outline-none">
            <option value="conservative">Conservative</option>
            <option value="moderate">Moderate</option>
            <option value="aggressive">Aggressive</option>
          </select>
        </label>
        <div className="flex gap-2 sm:col-span-2">
          <Button type="submit">Save goal</Button>
          <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>
        </div>
      </form>
    </Card>
  );
}

function HoldingForm({
  onSave,
  onCancel,
}: {
  onSave: (holding: Holding) => void;
  onCancel: () => void;
}) {
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");
  const [buyPrice, setBuyPrice] = useState("");
  return (
    <Card>
      <h3 className="font-display text-lg font-medium">Add holding</h3>
      <form
        className="mt-4 grid gap-3 sm:grid-cols-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (!ticker.trim() || !quantity || !buyPrice) return;
          onSave({
            ticker: ticker.trim().toUpperCase(),
            quantity: Number(quantity),
            buyPrice: Number(buyPrice),
          });
        }}
      >
        <label className="block">
          <span className="font-mono text-xs text-muted">Ticker</span>
          <input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} required
            placeholder="RELIANCE" className="mt-1 h-11 w-full rounded-sm border border-ink/20 bg-white px-3 font-mono focus:border-accent focus:outline-none" />
        </label>
        <label className="block">
          <span className="font-mono text-xs text-muted">Quantity</span>
          <input value={quantity} onChange={(e) => setQuantity(e.target.value)} required
            inputMode="decimal" placeholder="10" className="mt-1 h-11 w-full rounded-sm border border-ink/20 bg-white px-3 focus:border-accent focus:outline-none" />
        </label>
        <label className="block">
          <span className="font-mono text-xs text-muted">Buy price (₹)</span>
          <input value={buyPrice} onChange={(e) => setBuyPrice(e.target.value)} required
            inputMode="decimal" placeholder="1200" className="mt-1 h-11 w-full rounded-sm border border-ink/20 bg-white px-3 focus:border-accent focus:outline-none" />
        </label>
        <div className="flex gap-2 sm:col-span-3">
          <Button type="submit">Add holding</Button>
          <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>
        </div>
      </form>
    </Card>
  );
}

export default function PortfolioPage() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [analyzed, setAnalyzed] = useState<AnalyzedGoal[]>([]);
  const [totals, setTotals] = useState<{ invested: number; value: number; pnl: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showGoalForm, setShowGoalForm] = useState(false);
  const [holdingGoalId, setHoldingGoalId] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<Record<string, GoalSuggestResponse>>({});
  const [suggestingId, setSuggestingId] = useState<string | null>(null);

  const refresh = useCallback(async (nextGoals: Goal[]) => {
    setGoals(nextGoals);
    if (nextGoals.length === 0) {
      setAnalyzed([]);
      setTotals(null);
      return;
    }
    try {
      const res = await analyzePortfolio(nextGoals);
      setAnalyzed(res.goals);
      setTotals({ invested: res.totalInvested, value: res.totalCurrentValue, pnl: res.totalPnl });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not analyse the portfolio.");
    }
  }, []);

  useEffect(() => {
    loadPortfolio(USER_ID)
      .then(async (data) => {
        await refresh(data.goals ?? []);
      })
      .catch(() => setError("Could not load the portfolio. Is the API running?"))
      .finally(() => setLoading(false));
  }, [refresh]);

  const persist = async (nextGoals: Goal[]) => {
    await savePortfolio(USER_ID, nextGoals);
    await refresh(nextGoals);
  };

  const addGoal = async (goal: Goal) => {
    setShowGoalForm(false);
    await persist([...goals, goal]);
  };

  const addHolding = async (goalId: string, holding: Holding) => {
    setHoldingGoalId(null);
    await persist(
      goals.map((g) => (g.id === goalId ? { ...g, holdings: [...g.holdings, holding] } : g)),
    );
  };

  const suggest = async (goal: Goal) => {
    setSuggestingId(goal.id);
    try {
      const res = await suggestForGoal(goal);
      setSuggestions((prev) => ({ ...prev, [goal.id]: res }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suggestions failed.");
    } finally {
      setSuggestingId(null);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-medium tracking-tight sm:text-4xl">Portfolio</h1>
          <p className="mt-3 max-w-2xl text-[17px] leading-relaxed text-muted">
            Goals, holdings, P&amp;L and progress, with AI suggestions per goal.
          </p>
        </div>
        <Button onClick={() => setShowGoalForm(true)}>New goal</Button>
      </div>

      {totals && (
        <Card className="mt-8">
          <dl className="grid grid-cols-3 gap-3 text-center">
            <div>
              <dt className="font-mono text-[11px] uppercase tracking-wider text-muted">Invested</dt>
              <dd className="mt-1 font-mono text-lg">{formatCompactINR(totals.invested)}</dd>
            </div>
            <div>
              <dt className="font-mono text-[11px] uppercase tracking-wider text-muted">Current value</dt>
              <dd className="mt-1 font-mono text-lg">{formatCompactINR(totals.value)}</dd>
            </div>
            <div>
              <dt className="font-mono text-[11px] uppercase tracking-wider text-muted">Total P&amp;L</dt>
              <dd className={`mt-1 font-mono text-lg ${totals.pnl >= 0 ? "text-accent" : "text-[#c2402a]"}`}>
                {totals.pnl >= 0 ? "+" : ""}{formatCompactINR(totals.pnl)}
              </dd>
            </div>
          </dl>
        </Card>
      )}

      {error && (
        <div className="mt-6 rounded-sm border border-[#c2402a]/30 bg-[#c2402a]/[0.05] p-4" role="alert">
          <p className="text-sm text-[#c2402a]">{error}</p>
        </div>
      )}

      <div className="mt-6 space-y-4">
        {showGoalForm && <GoalForm onSave={addGoal} onCancel={() => setShowGoalForm(false)} />}
        {loading ? (
          <Skeleton className="h-64" />
        ) : analyzed.length === 0 ? (
          <PortfolioEmptyState onAddGoal={() => setShowGoalForm(true)} />
        ) : (
          analyzed.map((goal) => (
            <div key={goal.goalId}>
              <GoalCard
                goal={goal}
                onSuggest={suggest}
                onAddHolding={setHoldingGoalId}
                suggestion={suggestions[goal.goalId]}
                suggesting={suggestingId === goal.goalId}
              />
              {holdingGoalId === goal.goalId && (
                <div className="mt-4">
                  <HoldingForm
                    onSave={(h) => addHolding(goal.goalId, h)}
                    onCancel={() => setHoldingGoalId(null)}
                  />
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
