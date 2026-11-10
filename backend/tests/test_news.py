"""Tests for ticker handling and news combining (no network, no models)."""
from datetime import UTC, datetime, timedelta

from news import (
    build_ticker_terms,
    dedupe_news_rows,
    extract_search_phrase,
    extract_ticker,
    split_recent_and_historical,
)


def test_extract_ticker():
    assert extract_ticker("What is the sentiment on RELIANCE?") == "RELIANCE"
    assert extract_ticker("How is TCS doing?") == "TCS"
    assert extract_ticker("tell me about the market") == "MARKET"
    assert extract_ticker("") == "MARKET"


def test_extract_search_phrase():
    assert extract_search_phrase("What is the sentiment on RELIANCE?") == "RELIANCE"
    assert extract_search_phrase("How is TCS doing?") == "TCS"


def test_ticker_terms_include_aliases():
    terms = build_ticker_terms("RELIANCE")
    assert "reliance industries" in terms
    assert "ril" in terms
    assert "jio" in terms
    assert "reliance" in terms


def test_ticker_terms_for_company_name():
    terms = build_ticker_terms("HDFC Bank")
    assert "hdfcbank" in terms or "hdfc bank" in terms


def test_unknown_long_word_is_not_a_ticker():
    assert build_ticker_terms("SOMETHINGLONG") == []


def test_market_has_no_terms():
    assert build_ticker_terms("MARKET") == []


def test_dedupe_news_rows():
    rows = [
        {"Title": "Profit surges", "Date": "2026-11-10"},
        {"Title": "Profit surges", "Date": "2026-11-10"},
        {"Title": "Profit surges 25%", "Date": "2026-11-10"},
        {"Title": "Profit surges", "Date": "2026-11-09"},
        {"Title": "", "Date": "2026-11-10"},
    ]
    # Same title+date dedupes; the "25%" variant normalises to the same key;
    # a different date survives; an empty title is dropped.
    assert len(dedupe_news_rows(rows)) == 2


def test_split_recent_and_historical():
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    old = (datetime.now(UTC) - timedelta(days=400)).strftime("%Y-%m-%d")
    rows = [{"Title": "a", "Date": today}, {"Title": "b", "Date": old}]
    recent, historical = split_recent_and_historical(rows)
    assert [r["Title"] for r in recent] == ["a"]
    assert [r["Title"] for r in historical] == ["b"]
