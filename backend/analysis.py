"""Analysis pipeline — fast deterministic path first, LLM path on request.

Fast path: retrieve news, score it with the rule-based engine, decide
BUY/HOLD/SELL. No LLM call, so it works with no keys at all.

GenAI path (`USE_GENAI_ANALYSIS=true`): vector search (scout) hands the top
5 articles to one LLM call (analyst) that returns sentiment + decision +
explanation as JSON. Any failure falls back to the fast path. The two steps
run as plain functions — a graph library would add nothing to a linear
two-step flow.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import config
import llm
from embeddings import embed_query, get_chroma_collection
from news import (
    dedupe_news_rows,
    extract_search_phrase,
    extract_ticker,
    fetch_news_ondemand,
    retrieve_chroma_news,
    retrieve_local_news,
    split_recent_and_historical,
)
from price_service import fetch_peer_comparison, fetch_stock_price
from sentiment import (
    average_sentiment,
    build_explanation,
    compute_confidence,
    extract_drivers,
    latest_news_date,
    weighted_pattern_sentiment,
)

AI_SUMMARY_MAX_HEADLINES = 10


def generate_ai_summary(ticker: str, headlines: list[str],
                        sentiment: float) -> str | None:
    """2–3 sentence investor summary from the headlines. None on failure."""
    if not headlines:
        return None
    mood = "positive" if sentiment > 0.1 else "negative" if sentiment < -0.1 else "neutral"
    listed = "\n".join(f"- {h}" for h in headlines[:AI_SUMMARY_MAX_HEADLINES])
    prompt = (
        f"Analyze these news headlines for {ticker} stock and provide a concise "
        f"2-3 sentence summary for an investor. Focus on: 1. Key developments or "
        f"events 2. Market sentiment drivers 3. Potential impact on stock\n\n"
        f"Headlines:\n{listed}\n\nOverall sentiment: {mood} ({sentiment:.2f})\n\n"
        "Provide a brief, actionable summary (max 3 sentences):"
    )
    try:
        return llm.generate(prompt, temperature=0.5).strip() or None
    except Exception:
        return None


def _decide(sentiment: float, has_recent: bool) -> str:
    if not has_recent:
        return "HOLD"
    if sentiment >= config.BUY_THRESHOLD:
        return "BUY"
    if sentiment <= config.SELL_THRESHOLD:
        return "SELL"
    return "HOLD"


def run_fast_analysis(query: str) -> dict[str, Any]:
    search_phrase = extract_search_phrase(query)
    ticker = extract_ticker(query)
    match_key = search_phrase or ticker

    chroma_rows = retrieve_chroma_news(
        query, match_key, limit=config.FAST_NEWS_MAX_CANDIDATES)
    local_rows = retrieve_local_news(
        query, match_key, limit=config.FAST_NEWS_MAX_CANDIDATES)
    all_rows = dedupe_news_rows(chroma_rows + local_rows)
    recent_rows, historical_rows = split_recent_and_historical(all_rows)

    ondemand_fetched = False
    if not recent_rows and match_key and match_key != "MARKET":
        fetched = fetch_news_ondemand(match_key)
        if fetched:
            all_rows = dedupe_news_rows(all_rows + fetched)
            ondemand_fetched = True
            recent_rows, historical_rows = split_recent_and_historical(all_rows)

    recent_rows = recent_rows[:5]
    historical_rows = historical_rows[:5]
    pattern_rows = (recent_rows + historical_rows)[:config.FAST_NEWS_MAX_CANDIDATES]
    recent_count, pattern_count = len(recent_rows), len(pattern_rows)
    latest_date = latest_news_date(pattern_rows)

    no_data = recent_count == 0 and pattern_count == 0
    stale = recent_count == 0 and pattern_count > 0
    if no_data:
        stale_reason = (f"No news data found for '{match_key}'. This stock may not "
                        "have recent coverage in our data sources.")
    elif stale:
        stale_reason = (f"No recent matched headlines in the last "
                        f"{config.FAST_NEWS_MAX_AGE_DAYS} days.")
    else:
        stale_reason = ""
    if ondemand_fetched:
        stale_reason = (f"Recent live news fetched for '{match_key}'."
                        if recent_rows else
                        f"Live news lookup completed for '{match_key}', but no recent "
                        "matching headlines were returned.")

    news_rows = recent_rows if recent_rows else historical_rows
    retrieved_docs = [
        {"content": row.get("Description", ""),
         "metadata": {"Date": row.get("Date", ""), "Title": row.get("Title", "")},
         "distance": None}
        for row in news_rows
    ]

    now_sentiment = average_sentiment(recent_rows)
    pattern_sentiment = weighted_pattern_sentiment(pattern_rows)
    sentiment = (0.7 * now_sentiment + 0.3 * pattern_sentiment) if recent_rows \
        else pattern_sentiment * 0.35
    sentiment = max(-1.0, min(1.0, sentiment))
    decision = _decide(sentiment, bool(recent_rows))
    positive_drivers, negative_drivers = extract_drivers(pattern_rows)

    state: dict[str, Any] = {
        "query": query,
        "retrieved_docs": retrieved_docs,
        "sentiment": sentiment,
        "now_sentiment": max(-1.0, min(1.0, now_sentiment)),
        "pattern_sentiment": max(-1.0, min(1.0, pattern_sentiment)),
        "confidence": compute_confidence(recent_count, pattern_count),
        "recent_news_count": recent_count,
        "pattern_news_count": pattern_count,
        "latest_news_date": latest_date,
        "stale_data": stale or no_data,
        "stale_reason": stale_reason,
        "explanation": build_explanation(
            sentiment=sentiment, now_sentiment=now_sentiment,
            pattern_sentiment=pattern_sentiment, recent_count=recent_count,
            pattern_count=pattern_count, latest_news_date=latest_date,
            recommendation=decision, ondemand_fetched=ondemand_fetched,
            ticker=match_key, fast_news_max_age_days=config.FAST_NEWS_MAX_AGE_DAYS),
        "positive_drivers": positive_drivers,
        "negative_drivers": negative_drivers,
        "final_decision": decision,
    }
    return _enrich_state(state, match_key)


def _enrich_state(state: dict[str, Any], ticker: str) -> dict[str, Any]:
    """Add price, peers and AI summary. Each degrades to None, never raises."""
    if not ticker or ticker == "MARKET":
        state.update(current_price=None, price_change=None,
                     price_change_percent=None, peers=None, ai_summary=None)
        return state

    headlines = [d.get("metadata", {}).get("Title", "")
                 for d in state.get("retrieved_docs", [])]
    headlines = [h for h in headlines if h]
    price_data = {"current_price": None, "price_change": None,
                  "price_change_percent": None}
    ai_summary = None
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {"price": pool.submit(fetch_stock_price, ticker)}
        if config.ENABLE_AI_SUMMARY and headlines:
            futures["ai"] = pool.submit(
                generate_ai_summary, ticker, headlines, state.get("sentiment", 0.0))
        for key, future in futures.items():
            try:
                if key == "price":
                    price_data = future.result(timeout=10)
                else:
                    ai_summary = future.result(timeout=15)
            except Exception:
                pass
    state["current_price"] = price_data.get("current_price")
    state["price_change"] = price_data.get("price_change")
    state["price_change_percent"] = price_data.get("price_change_percent")
    state["ai_summary"] = ai_summary
    state["peers"] = fetch_peer_comparison(ticker)
    return state


# ─── GenAI path ─────────────────────────────────────────────────────────────

def _scout(query: str) -> list[dict[str, Any]]:
    """Vector search: top 5 semantically matching articles."""
    try:
        collection = get_chroma_collection()
        vector = embed_query(query)
        result = collection.query(
            query_embeddings=[vector], n_results=5,
            include=["documents", "metadatas", "distances"])
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return [
            {"content": doc,
             "metadata": metadatas[i] if i < len(metadatas) else {},
             "distance": distances[i] if i < len(distances) else None}
            for i, doc in enumerate(documents)
        ]
    except Exception:
        return []


def _analyst(query: str, docs: list[dict[str, Any]]) -> dict[str, Any]:
    """One LLM call: sentiment + decision + explanation as JSON."""
    if not docs:
        return {"sentiment": 0.0, "final_decision": "HOLD",
                "explanation": "No news data available for analysis."}
    joined = "\n\n".join(
        f"Title: {d.get('metadata', {}).get('Title', '')}\n"
        f"Date: {d.get('metadata', {}).get('Date', '')}\n"
        f"Content: {d.get('content', '')}" for d in docs)
    prompt = (
        "You are a financial analyst and investment advisor for Indian equities.\n\n"
        "Analyze the following news and provide:\n"
        "1. A sentiment score between -1 (very negative) and 1 (very positive)\n"
        "2. An investment decision: BUY, HOLD, or SELL\n"
        "3. A brief explanation (1-2 sentences)\n\n"
        "Respond with JSON only using this format:\n"
        '{"sentiment": <float>, "decision": "<BUY|HOLD|SELL>", '
        '"explanation": "<string>"}\n\n'
        f"User query: {query}\n\nNews:\n{joined}"
    )
    text = llm.call_with_quota_retry(
        lambda: llm.generate(prompt, temperature=0.3),
        operation="Analysis and decision generation")
    parsed = llm.parse_json_object(text) or {}
    sentiment = max(-1.0, min(1.0, float(parsed.get("sentiment", 0.0) or 0.0)))
    decision = str(parsed.get("decision", "HOLD")).upper()
    if decision not in {"BUY", "HOLD", "SELL"}:
        decision = "BUY" if "BUY" in text.upper() else \
            "SELL" if "SELL" in text.upper() else "HOLD"
    return {"sentiment": sentiment, "final_decision": decision,
            "explanation": str(parsed.get("explanation", ""))}


def run_genai_analysis(query: str) -> dict[str, Any]:
    docs = _scout(query)
    result = _analyst(query, docs)
    result["query"] = query
    result["retrieved_docs"] = docs
    ticker = extract_ticker(query)
    # Fill the fast-path fields the API contract promises.
    rows = [{"Title": d.get("metadata", {}).get("Title", ""),
             "Description": d.get("content", ""),
             "Date": d.get("metadata", {}).get("Date", "")} for d in docs]
    result.setdefault("now_sentiment", result["sentiment"])
    result.setdefault("pattern_sentiment", result["sentiment"])
    result.setdefault("confidence", compute_confidence(len(docs), len(docs)))
    result.setdefault("recent_news_count", len(docs))
    result.setdefault("pattern_news_count", len(docs))
    result.setdefault("latest_news_date", latest_news_date(rows))
    result.setdefault("stale_data", not docs)
    result.setdefault("stale_reason",
                      "" if docs else "No news data found in the vector store.")
    result.setdefault("positive_drivers", extract_drivers(rows)[0])
    result.setdefault("negative_drivers", extract_drivers(rows)[1])
    return _enrich_state(result, ticker)


def run_analysis(query: str) -> dict[str, Any]:
    if not config.USE_GENAI_ANALYSIS:
        return run_fast_analysis(query)
    try:
        return run_genai_analysis(query)
    except Exception:
        return run_fast_analysis(query)
