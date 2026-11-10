"""Explainable rule-based sentiment engine for financial news.

Scores a headline + description in [-1, 1] from a weighted lexicon, with
intensifiers, negation, contrast splits and numeric magnitude. No ML model,
so every score can be traced back to the words that produced it.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime

from stock_data import SOURCE_QUALITY_WEIGHTS

POSITIVE_TERMS: dict[str, float] = {
    "gain": 0.9, "gains": 0.9, "rise": 0.85, "rises": 0.85,
    "up": 0.5, "surge": 1.5, "surges": 1.5, "jump": 1.2, "jumps": 1.2,
    "beats": 1.0, "beat": 1.0, "strong": 0.8, "profit": 1.1, "profits": 1.1,
    "growth": 1.0, "bullish": 1.2, "buy": 1.0, "record": 1.2,
    "expands": 0.8, "expansion": 0.8, "outperform": 1.1, "outperforms": 1.1,
    "upgrade": 1.1, "upgrades": 1.1,
}

NEGATIVE_TERMS: dict[str, float] = {
    "fall": 0.9, "falls": 0.9, "down": 0.5, "drop": 1.0, "drops": 1.0,
    "slump": 1.4, "slumps": 1.4, "miss": 1.1, "misses": 1.1,
    "weak": 0.8, "loss": 1.2, "losses": 1.2, "decline": 1.0, "declines": 1.0,
    "bearish": 1.2, "sell": 1.0, "cuts": 0.9, "cut": 0.9, "risk": 0.9,
    "downgrade": 1.2, "downgrades": 1.2, "plunge": 1.7, "plunges": 1.7,
}

INTENSIFIERS: dict[str, float] = {
    "marginal": 0.65, "slight": 0.7, "slightly": 0.7, "modest": 0.8,
    "moderate": 0.9, "solid": 1.1, "strong": 1.2, "sharp": 1.3,
    "significant": 1.35, "substantial": 1.45, "massive": 1.6, "huge": 1.6,
    "record": 1.5, "extreme": 1.7,
}

NEGATIONS = {"no", "not", "never", "without", "hardly", "barely"}
CONTRASTS = {"but", "however", "despite", "although", "though", "yet"}
_CONTRAST_RE = re.compile(
    r"(?i)\b(?:but|however|despite|although|though|yet)\b"
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _magnitude_factor(text: str) -> float:
    """A big % move in the text scales the whole score."""
    percents = [
        float(m.group(1))
        for m in re.finditer(r"\b([0-9]+(?:\.[0-9]+)?)\s*%", text)
    ]
    if not percents:
        return 1.0
    peak = max(percents)
    if peak >= 100:
        return 1.6
    if peak >= 50:
        return 1.4
    if peak >= 20:
        return 1.25
    if peak >= 10:
        return 1.15
    return 1.0


def _score_segment(segment: str) -> tuple[float, float]:
    """Return (weighted score, total absolute weight) for one segment."""
    tokens = re.findall(r"[a-z]+", segment.lower())
    if not tokens:
        return 0.0, 0.0

    weighted = 0.0
    absolute = 0.0
    for idx, token in enumerate(tokens):
        if token in POSITIVE_TERMS:
            base = POSITIVE_TERMS[token]
        elif token in NEGATIVE_TERMS:
            base = -NEGATIVE_TERMS[token]
        else:
            continue

        lookback = tokens[max(0, idx - 3):idx]
        intensity = 1.0
        for prev in lookback:
            if prev in INTENSIFIERS:
                intensity *= INTENSIFIERS[prev]
        if any(prev in NEGATIONS for prev in lookback):
            base = -base

        contribution = base * intensity
        weighted += contribution
        absolute += abs(contribution)

    factor = _magnitude_factor(segment)
    weighted *= factor
    absolute *= max(1.0, factor * 0.9)
    return weighted, absolute


def compute_sentiment(text: str) -> float:
    """Score one piece of text in [-1, 1]. 0 when no sentiment terms match."""
    lowered = (text or "").lower()
    if not lowered.strip():
        return 0.0

    segments = _CONTRAST_RE.split(lowered)
    scores, weights = [], []
    for segment in segments:
        score, magnitude = _score_segment(segment)
        if magnitude <= 0:
            continue
        scores.append(score)
        weights.append(magnitude)
    if not scores:
        return 0.0

    # The last contrast segment carries the conclusion — boost it 1.2x.
    total, total_weight = 0.0, 0.0
    for idx, score in enumerate(scores):
        boost = 1.2 if idx == len(scores) - 1 and len(scores) > 1 else 1.0
        total += score * boost
        total_weight += weights[idx] * boost
    if total_weight <= 0:
        return 0.0
    return _clamp(total / total_weight, -1.0, 1.0)


def parse_datetime_text(value: str) -> datetime | None:
    """Parse the date formats news sources actually emit."""
    text = (value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        pass
    normalised = re.sub(r"\s+", " ", text)
    for fmt in ("%B %d, %Y, %A", "%B %d, %Y", "%b %d, %Y, %A",
                "%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalised, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _row_text(row: dict) -> str:
    return f"{row.get('Title', '')} {row.get('Description', '')}"


def average_sentiment(rows: list[dict]) -> float:
    if not rows:
        return 0.0
    return sum(compute_sentiment(_row_text(r)) for r in rows) / len(rows)


def _time_decay_weight(row: dict) -> float:
    parsed = parse_datetime_text(str(row.get("Date", "") or ""))
    if parsed is None:
        return 0.15
    age_days = max(0.0, (datetime.now(UTC) - parsed).total_seconds() / 86400.0)
    if age_days <= 7:
        base = 1.0
    elif age_days <= 90:
        base = 0.6
    elif age_days <= 365:
        base = 0.3
    else:
        base = 0.15
    source = str(row.get("Source", "") or "").strip().lower()
    return base * SOURCE_QUALITY_WEIGHTS.get(source, 1.0)


def weighted_pattern_sentiment(rows: list[dict]) -> float:
    if not rows:
        return 0.0
    weighted_sum = sum(
        compute_sentiment(_row_text(r)) * _time_decay_weight(r) for r in rows
    )
    total_weight = sum(_time_decay_weight(r) for r in rows)
    return weighted_sum / total_weight if total_weight > 0 else 0.0


def latest_news_date(rows: list[dict]) -> str:
    latest: datetime | None = None
    for row in rows:
        parsed = parse_datetime_text(str(row.get("Date", "") or ""))
        if parsed and (latest is None or parsed > latest):
            latest = parsed
    return latest.date().isoformat() if latest else ""


def compute_confidence(recent_count: int, pattern_count: int) -> float:
    score = 0.7 * min(1.0, recent_count / 5.0) + 0.3 * min(1.0, pattern_count / 40.0)
    return max(0.0, min(1.0, score))


def extract_drivers(rows: list[dict], limit: int = 3) -> tuple[list[str], list[str]]:
    scored = [
        (compute_sentiment(_row_text(r)), str(r.get("Title", "") or "").strip())
        for r in rows
    ]
    scored = [(s, t) for s, t in scored if t]
    positives = [t for s, t in sorted(scored, key=lambda x: x[0], reverse=True) if s > 0]
    negatives = [t for s, t in sorted(scored, key=lambda x: x[0]) if s < 0]
    return positives[:limit], negatives[:limit]


def build_explanation(
    sentiment: float,
    now_sentiment: float,
    pattern_sentiment: float,
    recent_count: int,
    pattern_count: int,
    latest_news_date: str,
    recommendation: str,
    ondemand_fetched: bool = False,
    ticker: str = "",
    fast_news_max_age_days: int = 30,
) -> str:
    if recent_count == 0 and pattern_count == 0:
        return (
            f"No news data found for '{ticker or 'this stock'}'. "
            f"Recommendation defaults to {recommendation} due to insufficient data. "
            "Try searching for a more common stock symbol or check back later."
        )
    if ondemand_fetched:
        return (
            f"Recommendation {recommendation} is based on {pattern_count} live-fetched "
            f"headlines (no cached data). Sentiment={sentiment:.2f} "
            f"(now={now_sentiment:.2f}, pattern={pattern_sentiment:.2f})."
        )
    if recent_count == 0 and pattern_count > 0:
        return (
            f"No recent matched headlines in the last {fast_news_max_age_days} days; "
            f"recommendation defaults to {recommendation} and uses historical pattern "
            f"context. Latest matched date: {latest_news_date or 'unknown'}."
        )
    return (
        f"Recommendation {recommendation} is based on combined sentiment={sentiment:.2f} "
        f"(now={now_sentiment:.2f}, pattern={pattern_sentiment:.2f}) using "
        f"{recent_count} recent and {pattern_count} total matched headlines."
    )
