"""Fixed-expectation tests for the rule-based sentiment engine.

Values below are hand-computed from the scoring rules (lexicon weights,
intensifiers, negation, contrast boost, numeric magnitude) — if the engine
changes, these numbers must change deliberately, not by accident.
"""
import pytest

from sentiment import (
    average_sentiment,
    build_explanation,
    compute_confidence,
    compute_sentiment,
    extract_drivers,
    latest_news_date,
    parse_datetime_text,
    weighted_pattern_sentiment,
)


def test_all_positive_terms_score_one():
    assert compute_sentiment("Reliance reports strong profit growth") == pytest.approx(1.0)


def test_all_negative_terms_score_minus_one():
    assert compute_sentiment("Shares plunge as company reports loss") == pytest.approx(-1.0)


def test_no_sentiment_terms_scores_zero():
    assert compute_sentiment("The company announced a meeting") == 0.0
    assert compute_sentiment("") == 0.0


def test_negation_flips_sign():
    assert compute_sentiment("No profit growth expected") == pytest.approx(-1.0)
    assert compute_sentiment("Company did not miss estimates") == pytest.approx(1.0)


def test_contrast_last_segment_wins():
    # "profit rises" (+1.95) then "losses mount" (-1.2, boosted 1.2x)
    # (1.95 - 1.44) / (1.95 + 1.44) = 0.1504
    assert compute_sentiment("Profit rises but losses mount") == pytest.approx(0.1504, abs=1e-3)


def test_intensifiers_shift_mixed_sentiment():
    plain = compute_sentiment("Surge but drop")
    intense = compute_sentiment("Massive surge but slight drop")
    assert plain == pytest.approx(0.1111, abs=1e-3)
    assert intense == pytest.approx(0.4815, abs=1e-3)
    assert intense > plain


def test_numeric_magnitude_shifts_mixed_sentiment():
    plain = compute_sentiment("Shares jump but fall")
    with_percent = compute_sentiment("Shares jump 25% but fall 5%")
    assert plain == pytest.approx(0.0526, abs=1e-3)
    assert with_percent == pytest.approx(0.1728, abs=1e-3)
    assert with_percent > plain


def test_parse_dates():
    assert parse_datetime_text("2026-11-10") is not None
    assert parse_datetime_text("November 10, 2026") is not None
    assert parse_datetime_text("Nov 10, 2026") is not None
    assert parse_datetime_text("") is None
    assert parse_datetime_text("not a date") is None


def test_average_and_weighted():
    rows = [
        {"Title": "Profit surges", "Description": "", "Date": "2026-11-10", "Source": "reuters"},
        {"Title": "Shares plunge", "Description": "", "Date": "2026-11-09", "Source": "reuters"},
    ]
    assert average_sentiment(rows) == pytest.approx(0.0)
    assert average_sentiment([]) == 0.0
    assert weighted_pattern_sentiment([]) == 0.0


def test_confidence():
    assert compute_confidence(5, 40) == pytest.approx(1.0)
    assert compute_confidence(0, 0) == 0.0
    assert compute_confidence(2, 10) == pytest.approx(0.355)


def test_latest_news_date():
    rows = [{"Date": "2026-11-09"}, {"Date": "2026-11-10"}, {"Date": "bad"}]
    assert latest_news_date(rows) == "2026-11-10"
    assert latest_news_date([]) == ""


def test_extract_drivers():
    rows = [
        {"Title": "Profit surges to record high", "Description": ""},
        {"Title": "Shares plunge on weak results", "Description": ""},
        {"Title": "Board meeting scheduled", "Description": ""},
    ]
    pos, neg = extract_drivers(rows)
    assert pos == ["Profit surges to record high"]
    assert neg == ["Shares plunge on weak results"]


def test_build_explanation_branches():
    assert "No news data found" in build_explanation(
        0.0, 0.0, 0.0, 0, 0, "", "HOLD", ticker="TCS")
    assert "live-fetched" in build_explanation(
        0.5, 0.5, 0.5, 3, 3, "2026-11-10", "BUY", ondemand_fetched=True, ticker="TCS")
    assert "No recent matched headlines" in build_explanation(
        0.1, 0.0, 0.1, 0, 4, "2026-10-01", "HOLD", ticker="TCS")
    assert "combined sentiment" in build_explanation(
        0.5, 0.6, 0.4, 3, 8, "2026-11-10", "BUY", ticker="TCS")
