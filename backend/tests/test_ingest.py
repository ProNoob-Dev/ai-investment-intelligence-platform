"""Tests for ticker tagging — macro news must not tag unrelated tickers."""
from ingest import detect_ticker_tags


def test_macro_news_gets_no_ticker():
    assert detect_ticker_tags(
        "Traders raise odds of 50 bps Fed rate hike as CPI rise exceeds expectations",
        "Persistent inflation worries as the Federal Reserve signals more hikes",
    ) == []
    assert detect_ticker_tags(
        "US consumer prices rise above expectations in October",
        "Federal Reserve officials press the rate hike case",
    ) == []
    assert detect_ticker_tags(
        "The amber light on the economy",
        "An amber signal for markets as growth slows",
    ) == []


def test_company_names_still_tag():
    assert detect_ticker_tags(
        "Persistent Systems Q2 profit rises 18%",
        "Persistent Systems reported strong deal wins",
    ) == ["PERSISTENT"]
    assert detect_ticker_tags(
        "Federal Bank Q2 net profit up 12%",
        "Federal Bank beat estimates",
    ) == ["FEDERALBNK"]
    assert detect_ticker_tags(
        "HUL dividend 2026: Tomorrow is the last day to buy",
        "Hindustan Unilever announces dividend record date",
    ) == ["HINDUNILVR"]


def test_caps_ticker_tokens_tag():
    assert detect_ticker_tags(
        "RELIANCE, TCS lead gains as Sensex rises",
        "Reliance Industries and Tata Consultancy Services rose in trade",
    ) == ["RELIANCE", "TCS"]
