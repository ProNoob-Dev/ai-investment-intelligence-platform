"""News retrieval for analysis: vector store + local CSV + on-demand lookup.

The fast analysis path never calls an LLM. It ranks candidate headlines by
ticker relevance, then recency, and splits them into a recent window and a
historical pattern window for the sentiment engine.
"""
from __future__ import annotations

import csv
import re
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import requests

import config
from embeddings import get_chroma_collection
from sentiment import parse_datetime_text
from stock_data import (
    GENERIC_STOCK_TERMS,
    QUERY_STOPWORDS,
    STOCK_ALIASES,
    TICKER_SUFFIX_SPLITS,
)

ONDEMAND_FETCH_TIMEOUT = 15
ONDEMAND_MAX_ARTICLES = 10


# ─── Ticker terms ────────────────────────────────────────────────────────────

def _normalize_term(term: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (term or "").lower()).strip()


def _contains_term(haystack: str, term: str) -> bool:
    norm = _normalize_term(term)
    if not norm:
        return False
    if " " in norm:
        return norm in haystack
    return re.search(rf"\b{re.escape(norm)}\b", haystack) is not None


def build_ticker_terms(ticker: str) -> list[str]:
    """All the ways a ticker can appear in a headline."""
    raw = (ticker or "").strip()
    if not raw or raw.upper() == "MARKET":
        return []
    upper = raw.upper()
    normalised = _normalize_term(raw)
    compact = re.sub(r"[^A-Z0-9]+", "", upper)

    terms: set[str] = set()
    if normalised:
        terms.add(normalised)
    if compact:
        terms.add(compact.lower())
    for part in normalised.split():
        if len(part) > 2 and part not in GENERIC_STOCK_TERMS:
            terms.add(part)
    for suffix in TICKER_SUFFIX_SPLITS:
        if compact.endswith(suffix) and len(compact) > len(suffix) + 1:
            prefix = compact[:-len(suffix)].strip()
            if prefix:
                terms.add(f"{prefix.lower()} {suffix.lower()}")
    if compact in STOCK_ALIASES:
        for alias in STOCK_ALIASES[compact]:
            if _normalize_term(alias):
                terms.add(_normalize_term(alias))
    for symbol, aliases in STOCK_ALIASES.items():
        for alias in aliases:
            if _normalize_term(alias) == normalised:
                terms.add(symbol.lower())
                for other in aliases:
                    if _normalize_term(other):
                        terms.add(_normalize_term(other))
    if len(compact) > 6 and compact not in STOCK_ALIASES and " " not in normalised:
        # A long unknown single word is probably not a ticker at all.
        return []
    return sorted(
        (t for t in terms if len(t) > 1
         and not (len(t) <= 4 and t in GENERIC_STOCK_TERMS)),
        key=len, reverse=True,
    )


def extract_ticker(query: str) -> str:
    """The ticker in a question. Prefers a known NSE symbol over the last
    all-caps word, so "How is TCS doing?" gives TCS, not DOING."""
    upper = (query or "").upper()
    match = re.search(r"\bON\s+([A-Z][A-Z0-9._-]{1,14})\b", upper)
    if match:
        return match.group(1)
    candidates = re.findall(r"\b[A-Z][A-Z0-9._-]{1,14}\b", upper)
    if not candidates:
        return "MARKET"
    for candidate in reversed(candidates):
        if candidate in STOCK_ALIASES:
            return candidate
    return candidates[-1]


def extract_search_phrase(query: str) -> str:
    upper = (query or "").upper().strip()
    if not upper:
        return ""
    match = re.search(r"\bON\s+(.+?)(?:\?|$)", upper)
    return match.group(1).strip() if match else extract_ticker(upper)


def _query_terms(query: str) -> list[str]:
    return [
        t for t in re.findall(r"[A-Za-z0-9]+", query.lower())
        if len(t) > 2 and t not in QUERY_STOPWORDS
    ]


def _score_row(haystack: str, ticker_terms: list[str], query_terms: list[str],
               ticker_tags: set[str] | None = None) -> tuple[int, bool]:
    """(relevance score, ticker matched). Tag hit beats text hit."""
    score, matched = 0, False
    for term in ticker_terms:
        compact = re.sub(r"[^a-z0-9]+", "", term.lower())
        if ticker_tags and compact and compact.upper() in ticker_tags:
            score += 6
            matched = True
            break
        if _contains_term(haystack, term):
            score += 5
            matched = True
            break
    for term in query_terms:
        if term in haystack:
            score += 1
    return score, matched


# ─── Sources ─────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_csv_rows() -> list[dict[str, str]]:
    path = config.NEWS_CSV_PATH if config.NEWS_CSV_PATH.exists() \
        else config.SEED_CSV_PATH
    if not path.exists():
        return []
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
        for row in csv.DictReader(f):
            rows.append({
                "Date": str(row.get("Date", "") or "").strip(),
                "Title": str(row.get("Title", "") or "").strip(),
                "Description": str(row.get("Description", "") or "").strip(),
                "Source": str(row.get("Source", "") or "historical_csv").strip(),
            })
    return rows


def retrieve_local_news(query: str, ticker: str, limit: int = 5) -> list[dict]:
    rows = _load_csv_rows()
    if not rows:
        return []
    query_terms = _query_terms(query)
    ticker_terms = build_ticker_terms(ticker)
    require_match = ticker != "MARKET"
    scored: list[tuple[int, float, dict]] = []
    for row in rows:
        parsed = parse_datetime_text(row.get("Date", ""))
        ts = parsed.timestamp() if parsed else 0.0
        haystack = _normalize_term(f"{row.get('Title', '')} {row.get('Description', '')}")
        score, matched = _score_row(haystack, ticker_terms, query_terms)
        if require_match and not matched:
            continue
        if score > 0:
            scored.append((score, ts, {**row, "Source": "historical_csv"}))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [r for _, _, r in scored[:limit]]


def retrieve_chroma_news(query: str, ticker: str, limit: int = 5) -> list[dict]:
    """Recent-window vector-store retrieval, ranked by ticker then recency."""
    try:
        collection = get_chroma_collection()
    except Exception:
        return []
    query_terms = _query_terms(query)
    ticker_terms = build_ticker_terms(ticker)
    require_match = ticker != "MARKET"
    cutoff = datetime.now(UTC) - timedelta(days=config.FAST_NEWS_MAX_AGE_DAYS)
    cutoff_date = cutoff.strftime("%Y-%m-%d")
    try:
        response = collection.get(
            where={"Date": {"$gte": cutoff_date}},
            limit=max(1500, limit * 20),
            include=["documents", "metadatas"],
        )
    except Exception:
        try:
            response = collection.get(
                limit=max(1500, limit * 20),
                include=["documents", "metadatas"],
            )
        except Exception:
            return []
    ids = response.get("ids", []) or []
    documents = response.get("documents", []) or []
    metadatas = response.get("metadatas", []) or []
    scored: list[tuple[int, float, dict]] = []
    for idx, _ in enumerate(ids):
        metadata = metadatas[idx] if idx < len(metadatas) and isinstance(metadatas[idx], dict) else {}
        title = str(metadata.get("Title", "") or "").strip()
        description = str(metadata.get("Description", "") or "").strip()
        if not description and idx < len(documents):
            description = str(documents[idx] or "").strip()
        date_value = str(metadata.get("Date", "") or "").strip()
        source = str(metadata.get("source", "") or "").strip()
        tags = {t.strip().upper() for t in str(metadata.get("ticker_tags", "") or "").split(",") if t.strip()}
        parsed = parse_datetime_text(str(metadata.get("published_at", "") or date_value))
        if parsed is None or parsed < cutoff:
            continue
        haystack = _normalize_term(f"{title} {description}")
        score, matched = _score_row(haystack, ticker_terms, query_terms, tags)
        if require_match and not matched:
            continue
        if score > 0:
            ts = parsed.timestamp()
            scored.append((score, ts, {"Date": date_value, "Title": title,
                                       "Description": description, "Source": source}))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [r for _, _, r in scored[:limit]]


def _search_terms_for_ticker(ticker: str) -> list[str]:
    terms = [ticker]
    upper = ticker.upper().strip()
    if upper in STOCK_ALIASES:
        terms.extend(STOCK_ALIASES[upper])
    for suffix in TICKER_SUFFIX_SPLITS:
        if upper.endswith(suffix) and len(upper) > len(suffix):
            base = upper[:-len(suffix)]
            if len(base) >= 2:
                terms.append(base)
            break
    return list(dict.fromkeys(terms))


def fetch_news_ondemand(ticker: str, limit: int = ONDEMAND_MAX_ARTICLES) -> list[dict]:
    """NewsAPI lookup for a ticker with no recent cached news. Needs a key."""
    if not config.NEWSAPI_KEY:
        return []
    terms = _search_terms_for_ticker(ticker)
    quoted = [f'"{t}"' if " " in t else t for t in terms[:5]]
    query = f"({' OR '.join(quoted)}) AND (India OR NSE OR BSE OR stock OR shares OR Sensex OR Nifty)"
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            headers={"X-Api-Key": config.NEWSAPI_KEY},
            params={"q": query,
                    "from": (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d"),
                    "language": "en", "sortBy": "relevancy",
                    "pageSize": min(limit * 3, 100)},
            timeout=ONDEMAND_FETCH_TIMEOUT,
        )
        if resp.status_code >= 400:
            return []
        payload = resp.json()
        if payload.get("status") != "ok":
            return []
    except Exception:
        return []
    match_terms = [t.lower() for t in terms]
    parsed: list[dict] = []
    for item in payload.get("articles", []):
        if len(parsed) >= limit:
            break
        title = str(item.get("title") or "").strip()
        description = str(item.get("description") or item.get("content") or "").strip()
        if not title or len(title) < 10 or len(description) < 20:
            continue
        if not any(t in f"{title} {description}".lower() for t in match_terms):
            continue
        parsed.append({
            "Date": str(item.get("publishedAt") or "")[:10],
            "Title": title,
            "Description": description or title,
            "Source": str((item.get("source") or {}).get("name") or "NewsAPI"),
        })
    return parsed


# ─── Combining ───────────────────────────────────────────────────────────────

def dedupe_news_rows(rows: list[dict]) -> list[dict]:
    def key(row: dict) -> str:
        title = re.sub(r"[^a-z0-9 ]+", " ", str(row.get("Title", "") or "").lower())
        title = re.sub(r"\b\d+(?:\.\d+)?\b", " ", title)
        title = re.sub(r"\s+", " ", title).strip()
        return f"{' '.join(title.split()[:12])}|{str(row.get('Date', '') or '').strip().lower()}"

    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        if not str(row.get("Title", "") or "").strip():
            continue
        k = key(row)
        if k in seen:
            continue
        seen.add(k)
        out.append(row)
    return out


def split_recent_and_historical(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    cutoff = datetime.now(UTC) - timedelta(days=config.FAST_NEWS_MAX_AGE_DAYS)
    recent, historical = [], []
    for row in rows:
        parsed = parse_datetime_text(str(row.get("Date", "") or ""))
        (recent if parsed is not None and parsed >= cutoff else historical).append(row)
    return recent, historical
