"""API smoke tests — mocked pipeline (no network, no models, no LLM keys)."""
import os

import pytest

# Isolate all file state (ChromaDB, JSON storage) into pytest's tmp dir.
os.environ["VECTOR_WEALTH_DB_PATH"] = os.path.join(
    os.environ.get("PYTEST_TMP", "/tmp"), "aiip_test_db")
os.environ["LIVE_NEWS_ENABLED"] = "false"
os.environ.pop("INCEPTION_API_KEY", None)
os.environ.pop("GOOGLE_API_KEY", None)

from fastapi.testclient import TestClient

import main
import portfolio

client = TestClient(main.app)

MOCK_ANALYSIS = {
    "sentiment": 0.45, "now_sentiment": 0.5, "pattern_sentiment": 0.3,
    "confidence": 0.8, "recent_news_count": 4, "pattern_news_count": 9,
    "latest_news_date": "2026-11-10", "stale_data": False, "stale_reason": "",
    "explanation": "Recommendation BUY is based on combined sentiment=0.45.",
    "positive_drivers": ["Profit surges"], "negative_drivers": [],
    "retrieved_docs": [
        {"content": "Profit surges", "metadata": {"Date": "2026-11-10", "Title": "Profit surges"}}],
    "final_decision": "BUY", "current_price": 1324.4, "price_change": 0.4,
    "price_change_percent": 0.03, "ai_summary": None,
    "peers": [{"ticker": "ONGC", "current_price": 100.0, "price_change": 1.0,
               "price_change_percent": 1.0}],
}


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"


def test_analyze_rejects_short_ticker():
    assert client.post("/analyze", json={"ticker": "AB"}).status_code == 400


def test_analyze_returns_contract(monkeypatch):
    monkeypatch.setattr(main, "run_analysis", lambda q: dict(MOCK_ANALYSIS))
    resp = client.post("/analyze", json={"ticker": "reliance"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "RELIANCE"
    assert body["recommendation"] == "BUY"
    assert body["sentiment"] == pytest.approx(0.45)
    assert body["current_price"] == pytest.approx(1324.4)
    assert body["news_references"] == [{"date": "2026-11-10", "title": "Profit surges"}]
    assert body["peers"][0]["ticker"] == "ONGC"


def test_opportunities_empty_initially():
    resp = client.get("/opportunities")
    assert resp.status_code == 200
    assert resp.json()["opportunities"] == []


def test_scanner_status():
    resp = client.get("/opportunities/status")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True


def test_portfolio_analyze_with_mock_prices(monkeypatch):
    monkeypatch.setattr(
        portfolio, "fetch_stock_price",
        lambda t: {"current_price": 1500.0, "price_change": 10.0, "price_change_percent": 0.67})
    goals = [{"id": "g1", "name": "Retirement", "targetAmount": 1000000,
              "targetDate": "2035-01-01", "riskTolerance": "moderate",
              "holdings": [{"ticker": "RELIANCE", "quantity": 10, "buyPrice": 1200.0}]}]
    resp = client.post("/portfolio/analyze", json={"goals": goals})
    assert resp.status_code == 200
    body = resp.json()
    assert body["totalInvested"] == pytest.approx(12000.0)
    assert body["totalCurrentValue"] == pytest.approx(15000.0)
    assert body["totalPnl"] == pytest.approx(3000.0)
    assert body["goals"][0]["progress"] == pytest.approx(1.5)


def test_storage_portfolio_roundtrip():
    goals = [{"id": "g1", "name": "Retirement", "targetAmount": 1000000,
              "targetDate": "2035-01-01", "riskTolerance": "moderate", "holdings": []}]
    save = client.post("/storage/portfolio/save", json={"user_id": "u1", "goals": goals})
    assert save.status_code == 200
    assert save.json()["goal_count"] == 1
    loaded = client.get("/storage/portfolio/load", params={"user_id": "u1"})
    assert loaded.status_code == 200
    assert loaded.json()["goals"][0]["name"] == "Retirement"


def test_chat_history_empty_session():
    resp = client.get("/chat/history/nonexistent-session")
    assert resp.status_code == 200
    assert resp.json()["messages"] == []


def test_chat_without_llm_is_503(monkeypatch):
    # Patch the loaded config, not just the environment: config reads .env
    # at import time, so a developer's .env would otherwise re-supply the key.
    import config

    monkeypatch.setattr(config, "INCEPTION_API_KEY", "")
    monkeypatch.setattr(config, "GOOGLE_API_KEY", "")
    resp = client.post("/chat", json={"message": "How is TCS doing?", "session_id": "s1"})
    assert resp.status_code == 503
