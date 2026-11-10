"""AI Investment Intelligence Platform — FastAPI app.

Endpoints: /analyze, /opportunities, /chat, /portfolio, /storage, /admin.
Background: live-news ingestion + opportunity scan on a schedule.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import traceback
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import config
from analysis import run_analysis
from chat import chat as chat_handler
from chat import get_or_create_session
from ingest import LiveNewsIngestor
from portfolio import analyze_goal, analyze_portfolio, suggest_for_goal
from scanner import is_market_hours, opportunity_scanner, should_run_scanner
from storage import load_chat_history, load_portfolio, save_chat_history, save_portfolio

logger = logging.getLogger("ai_investment")

app = FastAPI(title="AI Investment Intelligence Platform API", version="1.0.0")
live_news_ingestor = LiveNewsIngestor()

if config.ALLOWED_ORIGINS.strip() == "*":
    allowed_origins, origin_regex = ["*"], None
else:
    allowed_origins = [o.strip() for o in config.ALLOWED_ORIGINS.split(",") if o.strip()]
    origin_regex = r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"

app.add_middleware(
    CORSMiddleware, allow_origins=allowed_origins,
    allow_origin_regex=origin_regex, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


def verify_admin_key(request: Request):
    """X-Admin-Key gate for admin endpoints (open in dev when unset)."""
    if not config.ADMIN_API_KEY:
        return
    if request.headers.get("X-Admin-Key", "") != config.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing admin API key")


_rate_limit_store: dict[str, list[float]] = {}


def _check_rate_limit(client_ip: str) -> None:
    now = time.time()
    window_start = now - config.RATE_LIMIT_WINDOW_SECONDS
    hits = [ts for ts in _rate_limit_store.get(client_ip, []) if ts > window_start]
    if len(hits) >= config.RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {config.RATE_LIMIT_MAX} requests "
                   f"per {config.RATE_LIMIT_WINDOW_SECONDS}s.")
    hits.append(now)
    _rate_limit_store[client_ip] = hits


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={
        "error": "internal_server_error",
        "message": "An unexpected error occurred. Please try again later.",
        "detail": str(exc) if config.DEBUG else None,
    })


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


class AnalyzeRequest(BaseModel):
    ticker: str


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    context_data: dict[str, Any] | None = None


class HoldingInput(BaseModel):
    ticker: str
    quantity: float
    buyPrice: float
    buyDate: str = ""


class GoalInput(BaseModel):
    id: str = ""
    name: str
    targetAmount: float
    targetDate: str
    riskTolerance: str = "moderate"
    holdings: list[HoldingInput] = []


class PortfolioRequest(BaseModel):
    goals: list[GoalInput]


class GoalSuggestRequest(BaseModel):
    goal: GoalInput


class SavePortfolioRequest(BaseModel):
    user_id: str = "default"
    goals: list[GoalInput]


class SaveChatRequest(BaseModel):
    session_id: str
    messages: list[dict[str, Any]]


async def _live_news_scheduler_loop() -> None:
    while True:
        summary = await asyncio.to_thread(live_news_ingestor.ingest_once)
        should_scan, scan_reason = should_run_scanner()
        if should_scan and not summary.failed:
            try:
                scan_result = await asyncio.to_thread(opportunity_scanner.scan, scan_reason)
                print(json.dumps({
                    "event": "opportunity_scan", "timestamp": datetime.now(UTC).isoformat(),
                    "scan_type": scan_reason,
                    "candidates_found": scan_result.candidates_found,
                    "opportunities_found": len(scan_result.opportunities),
                    "success": scan_result.success}, ensure_ascii=False))
            except Exception as exc:
                print(json.dumps({"event": "opportunity_scan_error", "error": str(exc)}))
        sleep_seconds = live_news_ingestor.interval_minutes * 60
        if summary.failed:
            sleep_seconds = min(300, sleep_seconds)
        await asyncio.sleep(max(10, sleep_seconds))


@app.on_event("startup")
async def _startup_live_news_scheduler() -> None:
    if live_news_ingestor.enabled:
        app.state.live_news_task = asyncio.create_task(_live_news_scheduler_loop())


@app.on_event("shutdown")
async def _shutdown_live_news_scheduler() -> None:
    task = getattr(app.state, "live_news_task", None)
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@app.get("/")
async def root():
    return {
        "name": "AI Investment Intelligence Platform API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "POST /analyze": "Analyze a stock ticker",
            "POST /chat": "Stock research chat assistant",
            "GET /opportunities": "Get AI-identified opportunities",
            "POST /opportunities/scan": "Trigger opportunity scan",
            "GET /opportunities/status": "Scanner status",
            "GET /admin/live-news/status": "News ingestion status (requires X-Admin-Key)",
        },
    }


@app.post("/analyze")
def analyze_ticker(payload: AnalyzeRequest, request: Request):
    _check_rate_limit(_client_ip(request))
    started_at = time.perf_counter()
    ticker = payload.ticker.strip().upper()
    if len(ticker) < 3:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ticker: '{ticker}'. Ticker must be at least 3 characters "
                   "(e.g., MARUTI, TCS, INFY).")
    try:
        result = run_analysis(f"What is the sentiment on {ticker}?")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    references = [{"date": doc.get("metadata", {}).get("Date", ""),
                   "title": doc.get("metadata", {}).get("Title", "")}
                  for doc in result.get("retrieved_docs", [])]
    response_body = {
        "ticker": ticker, "query": f"What is the sentiment on {ticker}?",
        "sentiment": result.get("sentiment", 0.0),
        "now_sentiment": result.get("now_sentiment", result.get("sentiment", 0.0)),
        "pattern_sentiment": result.get("pattern_sentiment", result.get("sentiment", 0.0)),
        "confidence": result.get("confidence", 0.0),
        "recent_news_count": result.get("recent_news_count", len(references)),
        "pattern_news_count": result.get("pattern_news_count", len(references)),
        "latest_news_date": result.get("latest_news_date", ""),
        "stale_data": result.get("stale_data", False),
        "stale_reason": result.get("stale_reason", ""),
        "explanation": result.get("explanation", ""),
        "positive_drivers": result.get("positive_drivers", []),
        "negative_drivers": result.get("negative_drivers", []),
        "news_references": references,
        "recommendation": result.get("final_decision", "HOLD"),
        "current_price": result.get("current_price"),
        "price_change": result.get("price_change"),
        "price_change_percent": result.get("price_change_percent"),
        "ai_summary": result.get("ai_summary"),
        "peers": result.get("peers"),
    }
    print(json.dumps({
        "event": "analyze_request", "timestamp": datetime.now(UTC).isoformat(),
        "ticker": ticker, "recommendation": response_body["recommendation"],
        "sentiment": response_body["sentiment"],
        "recent_news_count": response_body["recent_news_count"],
        "pattern_news_count": response_body["pattern_news_count"],
        "stale_data": response_body["stale_data"],
        "latency_ms": round((time.perf_counter() - started_at) * 1000, 2)},
        ensure_ascii=False))
    return response_body


@app.get("/admin/live-news/status", dependencies=[Depends(verify_admin_key)])
def live_news_status():
    return live_news_ingestor.get_status()


@app.post("/admin/live-news/refresh", dependencies=[Depends(verify_admin_key)])
async def refresh_live_news():
    summary = await asyncio.to_thread(live_news_ingestor.ingest_once)
    if summary.failed:
        raise HTTPException(status_code=503, detail=summary.message)
    return summary.to_dict()


@app.post("/admin/live-news/retag-existing", dependencies=[Depends(verify_admin_key)])
async def retag_existing_live_news():
    result = await asyncio.to_thread(live_news_ingestor.retag_existing_records)
    if result.get("failed"):
        raise HTTPException(status_code=503, detail=result.get("message", "Retagging failed"))
    return result


@app.get("/opportunities")
async def get_opportunities():
    return {"opportunities": opportunity_scanner.get_opportunities(),
            "is_market_hours": is_market_hours()}


@app.get("/opportunities/status")
async def get_scanner_status():
    return opportunity_scanner.get_status()


@app.post("/opportunities/scan")
async def trigger_scan():
    should_scan, scan_reason = should_run_scanner()
    if not should_scan:
        scan_reason = "manual"
    scan_result = await asyncio.to_thread(opportunity_scanner.scan, scan_reason)
    if not scan_result.success:
        raise HTTPException(status_code=503, detail=scan_result.message)
    return scan_result.to_dict()


@app.post("/chat")
async def chat_endpoint(payload: ChatRequest, request: Request):
    _check_rate_limit(_client_ip(request))
    try:
        result = await asyncio.to_thread(
            chat_handler, payload.session_id, payload.message, payload.context_data)
        return result.to_dict()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/chat/history/{session_id}")
def chat_history(session_id: str):
    session = get_or_create_session(session_id)
    return {"session_id": session.session_id,
            "messages": [m.to_dict() for m in session.messages]}


@app.post("/portfolio/analyze")
async def portfolio_analyze(payload: PortfolioRequest, request: Request):
    _check_rate_limit(_client_ip(request))
    try:
        return await asyncio.to_thread(
            analyze_portfolio, [g.model_dump() for g in payload.goals])
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/portfolio/suggest")
async def portfolio_suggest(payload: GoalSuggestRequest, request: Request):
    _check_rate_limit(_client_ip(request))
    goal_dict = payload.goal.model_dump()
    try:
        analysis = await asyncio.to_thread(analyze_goal, goal_dict)
        result = await asyncio.to_thread(suggest_for_goal, analysis)
        return {"goalId": goal_dict.get("id", ""),
                "suggestion": result.get("suggestion", ""),
                "recommended_stocks": result.get("recommended_stocks", [])}
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/storage/portfolio/save")
def storage_save_portfolio(payload: SavePortfolioRequest):
    return save_portfolio(payload.user_id, [g.model_dump() for g in payload.goals])


@app.get("/storage/portfolio/load")
def storage_load_portfolio(user_id: str = "default"):
    return load_portfolio(user_id)


@app.post("/storage/chat/save")
def storage_save_chat(payload: SaveChatRequest):
    return save_chat_history(payload.session_id, payload.messages)


@app.get("/storage/chat/load")
def storage_load_chat(session_id: str):
    return load_chat_history(session_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
