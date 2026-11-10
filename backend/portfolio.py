"""Goal-based portfolio: P&L per holding, progress per goal, AI suggestions.

A goal is {id, name, targetAmount, targetDate, riskTolerance, holdings[]};
a holding is {ticker, quantity, buyPrice, buyDate}. Prices are fetched live;
a missing price falls back to the buy price (P&L 0) instead of failing.
"""
from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

import llm
from embeddings import get_chroma_collection
from price_service import fetch_stock_price
from sentiment import compute_sentiment

logger = logging.getLogger("ai_investment.portfolio")


def _years_until(target_date: str) -> float:
    try:
        target = datetime.fromisoformat((target_date or "").replace("Z", "+00:00"))
        if target.tzinfo is None:
            target = target.replace(tzinfo=UTC)
    except (ValueError, AttributeError):
        try:
            target = datetime(int(str(target_date)[:4]), 1, 1, tzinfo=UTC)
        except Exception:
            return 10.0
    return max(0.0, (target - datetime.now(UTC)).days / 365.25)


def _risk_label(risk: str) -> str:
    r = (risk or "moderate").lower().strip()
    if r in ("conservative", "low"):
        return "conservative"
    if r in ("aggressive", "high"):
        return "aggressive"
    return "moderate"


def analyze_goal(goal: dict[str, Any]) -> dict[str, Any]:
    def analyze_holding(h: dict[str, Any]) -> dict[str, Any]:
        ticker = str(h.get("ticker", "")).upper()
        qty = float(h.get("quantity", 0) or 0)
        buy_price = float(h.get("buyPrice", 0) or 0)
        invested = qty * buy_price
        price = fetch_stock_price(ticker)
        current_price = price.get("current_price")
        if current_price and current_price > 0:
            current_value = qty * current_price
            pnl = current_value - invested
            pnl_pct = (pnl / invested * 100) if invested > 0 else 0.0
        else:
            current_value, current_price, pnl, pnl_pct = invested, buy_price, 0.0, 0.0
        return {
            "ticker": ticker, "quantity": qty, "buyPrice": buy_price,
            "currentPrice": current_price, "invested": round(invested, 2),
            "currentValue": round(current_value, 2), "pnl": round(pnl, 2),
            "pnlPercent": round(pnl_pct, 2),
            "priceChange": price.get("price_change"),
            "priceChangePercent": price.get("price_change_percent"),
            "_invested": invested, "_current": current_value,
        }

    holdings = goal.get("holdings", []) or []
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(analyze_holding, holdings))
    total_invested = sum(r.pop("_invested") for r in results)
    total_current = sum(r.pop("_current") for r in results)
    target = float(goal.get("targetAmount", 0) or 0)
    total_pnl = total_current - total_invested
    return {
        "goalId": goal.get("id", ""), "goalName": goal.get("name", ""),
        "targetAmount": target, "targetDate": goal.get("targetDate", ""),
        "riskTolerance": _risk_label(goal.get("riskTolerance", "moderate")),
        "yearsLeft": round(_years_until(goal.get("targetDate", "")), 1),
        "totalInvested": round(total_invested, 2),
        "totalCurrentValue": round(total_current, 2),
        "totalPnl": round(total_pnl, 2),
        "totalPnlPercent": round((total_pnl / total_invested * 100) if total_invested > 0 else 0, 2),
        "progress": round(min((total_current / target * 100) if target > 0 else 0, 100), 1),
        "holdings": results,
    }


def analyze_portfolio(goals: list[dict[str, Any]]) -> dict[str, Any]:
    with ThreadPoolExecutor(max_workers=4) as pool:
        analyzed = list(pool.map(analyze_goal, goals))
    total_invested = sum(g["totalInvested"] for g in analyzed)
    total_current = sum(g["totalCurrentValue"] for g in analyzed)
    return {"goals": analyzed, "totalInvested": round(total_invested, 2),
            "totalCurrentValue": round(total_current, 2),
            "totalPnl": round(total_current - total_invested, 2),
            "goalCount": len(analyzed)}


def _extract_recommended_stocks(text: str) -> tuple[str, list[dict]]:
    for pattern in (r"RECOMMENDED_STOCKS:\s*```json\s*(\[.*?\])\s*```",
                    r"RECOMMENDED_STOCKS:\s*(\[.*?\])"):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return text[:match.start()].strip(), json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
    return text, []


def _holding_sentiments(holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        collection = get_chroma_collection()
    except Exception:
        collection = None
    insights = []
    for h in holdings:
        ticker = h["ticker"]
        sentiment = 0.0
        if collection is not None:
            try:
                result = collection.query(query_texts=[ticker], n_results=5,
                                          include=["documents"])
                docs = (result.get("documents") or [[]])[0]
                text = " ".join(docs) if docs else ""
                sentiment = compute_sentiment(text) if text else 0.0
            except Exception:
                sentiment = 0.0
        insights.append({
            "ticker": ticker, "sentiment": round(sentiment, 2),
            "pnl": h.get("pnl", 0), "pnlPercent": h.get("pnlPercent", 0),
            "weight": 0.0,  # filled in by suggest_for_goal once totals are known
        })
    return insights


def _rule_based_suggestions(goal_name: str, risk: str,
                            insights: list[dict[str, Any]]) -> str:
    suggestions = []
    for hi in insights:
        if hi["sentiment"] < -0.2 and risk == "conservative":
            suggestions.append(
                f"{hi['ticker']} shows negative sentiment ({hi['sentiment']:.2f}). "
                f"Consider reviewing for your {risk} goal.")
        elif hi["weight"] > 40:
            suggestions.append(
                f"{hi['ticker']} is {hi['weight']:.0f}% of this goal — "
                "consider diversifying to reduce concentration risk.")
    return "\n".join(suggestions) or \
        "Your holdings look balanced for this goal. Keep monitoring."


def suggest_for_goal(goal_analysis: dict[str, Any]) -> dict[str, Any]:
    risk = goal_analysis.get("riskTolerance", "moderate")
    years_left = goal_analysis.get("yearsLeft", 10)
    progress = goal_analysis.get("progress", 0)
    holdings = goal_analysis.get("holdings", [])
    goal_name = goal_analysis.get("goalName", "Goal")
    target = goal_analysis.get("targetAmount", 0)
    if not holdings:
        return {"suggestion": f"No holdings assigned to '{goal_name}' yet. "
                              "Add stocks to get personalized suggestions.",
                "recommended_stocks": []}

    total_value = goal_analysis.get("totalCurrentValue", 0) or 1
    insights = _holding_sentiments(holdings)
    for hi, h in zip(insights, holdings):
        hi["weight"] = h.get("currentValue", 0) / total_value * 100

    insights_text = "\n".join(
        f"- {hi['ticker']}: sentiment={hi['sentiment']:.2f}, "
        f"P&L={hi['pnlPercent']:.1f}%, weight={hi['weight']:.0f}%"
        for hi in insights)
    risk_guidance = {
        "conservative": "Prioritize capital preservation. Flag any holding with negative "
                        "sentiment immediately. Suggest blue-chip alternatives.",
        "moderate": "Balance growth and safety. Flag significant negative sentiment. "
                    "Suggest diversification if overweight in a sector.",
        "aggressive": "Focus on growth. Only flag severe negative sentiment. "
                      "Higher volatility is acceptable for better returns.",
    }
    prompt = (
        f"Analyze this investment goal and give 2–3 brief, actionable suggestions.\n\n"
        f"GOAL: {goal_name}\nTarget: ₹{target:,.0f} | Progress: {progress:.1f}% | "
        f"Years left: {years_left:.1f}\nRisk tolerance: {risk}\n"
        f"Amount remaining: ₹{max(0, target - goal_analysis.get('totalCurrentValue', 0)):,.0f}\n\n"
        f"HOLDINGS:\n{insights_text}\n\nGUIDELINES:\n"
        f"{risk_guidance.get(risk, risk_guidance['moderate'])}\n\n"
        "Keep suggestions short (1-2 sentences each), specific to this goal. Use ₹ symbol.\n\n"
        "IMPORTANT: After your suggestions text, you MUST also output a block of exactly 2-4 "
        "specific Indian stock (NSE) recommendations that complement the existing holdings. "
        "Consider the risk tolerance, remaining amount, and diversification. Use this EXACT format:\n\n"
        "RECOMMENDED_STOCKS:\n```json\n[\n  {\"ticker\": \"SYMBOL\", \"quantity\": 10, "
        "\"buyPrice\": 1234.50, \"reasoning\": \"Brief reason\"},\n  ...\n]\n```\n\n"
        "Rules for recommended stocks:\n"
        "- Use NSE ticker symbols (e.g. TCS, RELIANCE, INFY, HDFCBANK, WIPRO, etc.)\n"
        f"- Do NOT recommend stocks already held in this goal: "
        f"{', '.join(h['ticker'] for h in holdings)}\n"
        "- quantity should be a whole number, affordable given the remaining target amount\n"
        "- buyPrice should be approximate current market price in ₹\n"
        "- reasoning should be 1 short sentence"
    )
    try:
        raw = llm.generate(prompt, temperature=0.5)
        suggestion, stocks = _extract_recommended_stocks(raw.strip())
        return {"suggestion": suggestion, "recommended_stocks": stocks}
    except Exception as exc:
        logger.error("Suggestion generation failed: %s", exc)
        return {"suggestion": _rule_based_suggestions(goal_name, risk, insights),
                "recommended_stocks": []}
