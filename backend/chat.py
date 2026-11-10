"""Research chat — intent routing over the live pipeline.

Two LLM calls per data question: the first (temperature 0.3) decides the
intent and emits a tag; the second (temperature 0.7) turns fetched live data
into a conversational answer. General questions are answered directly.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import llm

logger = logging.getLogger("ai_investment.chat")

MAX_CONVERSATION_HISTORY = 20

SYSTEM_PROMPT = """You are the Stock Research Assistant — a helpful, concise expert on the Indian stock market.

CAPABILITIES:
- Analyze individual stocks (sentiment, price, news)
- Compare stocks or sectors
- Explain market concepts
- Discuss watchlist stocks
- Surface opportunities from recent scans

RULES:
1. When the user asks about a specific stock, respond with "[ANALYZE:TICKER]" FIRST, then I'll inject real data for you to discuss.
2. When comparing stocks, respond with "[COMPARE:TICKER1,TICKER2]".
3. When asked about watchlist, respond with "[WATCHLIST]".
4. When asked about their portfolio or financial goals, respond with "[PORTFOLIO]".
5. When asked about opportunities/discoveries, respond with "[OPPORTUNITIES]".
6. For general market questions or concepts, answer directly from your knowledge.
6. Keep responses concise — 2-4 short paragraphs max.
7. Use ₹ for Indian rupee prices.
8. Be conversational but professional.
9. If you don't know something specific, say so honestly.
10. IMPORTANT: Only output the intent tag when you need real-time data. For general questions, just answer directly."""


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: str = ""
    data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {"role": self.role, "content": self.content, "timestamp": self.timestamp}
        if self.data:
            d["data"] = self.data
        return d


@dataclass
class ChatSession:
    session_id: str
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: str = ""

    def add_message(self, msg: ChatMessage) -> None:
        self.messages.append(msg)
        if len(self.messages) > MAX_CONVERSATION_HISTORY:
            self.messages = self.messages[-MAX_CONVERSATION_HISTORY:]


_sessions: dict[str, ChatSession] = {}


def get_or_create_session(session_id: str) -> ChatSession:
    if session_id not in _sessions:
        _sessions[session_id] = ChatSession(
            session_id=session_id, created_at=datetime.now(UTC).isoformat())
    return _sessions[session_id]


def _detect_intent(response_text: str) -> tuple[str, str | None]:
    if m := re.search(r"\[ANALYZE:([A-Z0-9._&-]+)\]", response_text):
        return "analyze", m.group(1)
    if m := re.search(r"\[COMPARE:([A-Z0-9._&,-]+)\]", response_text):
        return "compare", m.group(1)
    if "[WATCHLIST]" in response_text:
        return "watchlist", None
    if "[PORTFOLIO]" in response_text:
        return "portfolio", None
    if "[OPPORTUNITIES]" in response_text:
        return "opportunities", None
    return "direct", None


def _fetch_analysis(ticker: str) -> dict[str, Any]:
    from analysis import run_analysis
    result = run_analysis(f"What is the sentiment on {ticker}?")
    return {
        "ticker": ticker, "sentiment": result.get("sentiment", 0.0),
        "now_sentiment": result.get("now_sentiment", 0.0),
        "confidence": result.get("confidence", 0.0),
        "recommendation": result.get("final_decision", "HOLD"),
        "current_price": result.get("current_price"),
        "price_change": result.get("price_change"),
        "price_change_percent": result.get("price_change_percent"),
        "recent_news_count": result.get("recent_news_count", 0),
        "positive_drivers": result.get("positive_drivers", [])[:3],
        "negative_drivers": result.get("negative_drivers", [])[:3],
        "ai_summary": result.get("ai_summary"),
        "explanation": result.get("explanation", ""),
    }


def _format_data_context(intent: str, data: Any) -> str:
    if intent == "analyze" and isinstance(data, dict):
        price = f"₹{data['current_price']:.2f}" if data.get("current_price") else "N/A"
        change = ""
        if data.get("price_change") is not None:
            sign = "+" if data["price_change"] >= 0 else ""
            change = f" ({sign}{data['price_change']:.2f}, {sign}{data.get('price_change_percent', 0):.2f}%)"
        pos = ", ".join(data.get("positive_drivers", [])[:3]) or "None"
        neg = ", ".join(data.get("negative_drivers", [])[:3]) or "None"
        return (f"[LIVE DATA for {data['ticker']}]\nPrice: {price}{change}\n"
                f"Sentiment: {data['sentiment']:.2f} (Confidence: {data['confidence']:.0%})\n"
                f"Recommendation: {data['recommendation']}\n"
                f"Recent articles: {data['recent_news_count']}\n"
                f"Positive drivers: {pos}\nNegative drivers: {neg}\n"
                f"{'AI Summary: ' + data['ai_summary'] if data.get('ai_summary') else ''}")
    if intent == "compare" and isinstance(data, list):
        parts = []
        for d in data:
            price = f"₹{d['current_price']:.2f}" if d.get("current_price") else "N/A"
            parts.append(f"- {d['ticker']}: Price {price}, Sentiment {d['sentiment']:.2f}, "
                         f"Rec: {d['recommendation']}")
        return "[COMPARISON DATA]\n" + "\n".join(parts)
    if intent == "opportunities" and isinstance(data, list):
        if not data:
            return "[OPPORTUNITIES] No opportunities found in the latest scan."
        return "[OPPORTUNITIES DATA]\n" + "\n".join(
            f"- {o['ticker']}: Sentiment {o.get('sentiment', 0):.2f}, {o.get('reasoning', '')}"
            for o in data[:5])
    return ""


def _portfolio_context(context_data: dict[str, Any] | None) -> str:
    if not context_data or not context_data.get("portfolio"):
        return ""
    parts = ["\n\nUSER'S PORTFOLIO (always available to you):"]
    for g in context_data["portfolio"]:
        parts.append(f"- Goal '{g.get('name', 'Unnamed')}': Target "
                     f"₹{g.get('targetAmount', 0):,.0f}, Risk: {g.get('riskTolerance', 'moderate')}, "
                     f"Target date: {g.get('targetDate', '')}")
        for h in g.get("holdings", []):
            parts.append(f"  {h.get('ticker', '?')} (qty: {h.get('quantity', 0)}, "
                         f"buy ₹{h.get('buyPrice', 0):.0f})")
    return "\n".join(parts)


def chat(session_id: str, user_message: str,
         context_data: dict[str, Any] | None = None) -> ChatMessage:
    session = get_or_create_session(session_id)
    session.add_message(ChatMessage(role="user", content=user_message,
                                    timestamp=datetime.now(UTC).isoformat()))

    messages = [{"role": "system",
                 "content": SYSTEM_PROMPT + _portfolio_context(context_data)}]
    messages += [{"role": m.role, "content": m.content} for m in session.messages]

    intent_response = llm.chat(messages, temperature=0.3)
    intent, payload = _detect_intent(intent_response)
    response_data: Any = None

    def discuss(data_context: str, instruction: str) -> str:
        follow_up = messages + [
            {"role": "assistant", "content": intent_response},
            {"role": "user", "content": f"{instruction}\n\n{data_context}"}]
        return llm.chat(follow_up, temperature=0.7)

    if intent == "analyze" and payload:
        try:
            response_data = _fetch_analysis(payload)
            final = discuss(_format_data_context("analyze", response_data),
                            "Here is the live data. Now give me a helpful, conversational "
                            "summary based on this data. Do NOT include raw numbers dump — "
                            "weave them naturally into your response:")
        except Exception as exc:
            final = (f"I tried to fetch data for {payload} but ran into an issue: {exc}. "
                     "Would you like me to try again?")
    elif intent == "compare" and payload:
        try:
            response_data = [_fetch_analysis(t.strip())
                             for t in payload.split(",")[:3]]
            final = discuss(_format_data_context("compare", response_data),
                            "Here is the comparison data. Provide a helpful comparison:")
        except Exception as exc:
            final = f"I couldn't fetch comparison data: {exc}. Want me to try again?"
    elif intent == "opportunities":
        try:
            from scanner import opportunity_scanner
            response_data = opportunity_scanner.get_opportunities()
            final = discuss(_format_data_context("opportunities", response_data),
                            "Here are the latest opportunities. Summarize them conversationally:")
        except Exception as exc:
            final = f"Couldn't fetch opportunities: {exc}"
    elif intent == "watchlist":
        final = ("I can see your watchlist! To analyze a specific stock from it, "
                 "just tell me the ticker — for example, 'How is TCS doing?'")
    elif intent == "portfolio":
        if not context_data or not context_data.get("portfolio"):
            final = ("I don't have access to your portfolio data right now. "
                     "Please add some goals and holdings in the Portfolio tab first!")
        else:
            try:
                from portfolio import analyze_portfolio
                analysis = analyze_portfolio(context_data["portfolio"])
                text = (f"Total Invested: ₹{analysis['totalInvested']}\n"
                        f"Total Value: ₹{analysis['totalCurrentValue']}\n"
                        f"Total P&L: ₹{analysis['totalPnl']}\n\nGoals:\n")
                for g in analysis["goals"]:
                    text += (f"- {g['goalName']}: Target ₹{g['targetAmount']}, "
                             f"Progress {g['progress']}%, Risk: {g['riskTolerance']}\n")
                    if g["holdings"]:
                        text += f"  Holdings: {', '.join(h['ticker'] for h in g['holdings'])}\n"
                final = discuss(text, "Here is the user's live portfolio data. Give a "
                                      "conversational, helpful overview, highlighting their "
                                      "progress and any risks based on their goals:")
            except Exception:
                logger.exception("Portfolio chat failed")
                final = "I hit an error trying to analyze your portfolio."
    else:
        final = intent_response

    final = re.sub(r"\[(?:ANALYZE|COMPARE|WATCHLIST|OPPORTUNITIES|PORTFOLIO)[^\]]*\]\s*",
                   "", final).strip()
    assistant_msg = ChatMessage(role="assistant", content=final,
                                timestamp=datetime.now(UTC).isoformat(),
                                data=response_data)
    session.add_message(assistant_msg)
    return assistant_msg
