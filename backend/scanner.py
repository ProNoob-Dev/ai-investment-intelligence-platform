"""Opportunity scanner — script filter first, LLM selection second.

Step 1 scores every ticker's last-48h news with the rule engine and keeps
sentiment above threshold. Step 2 asks the LLM to pick the top 5 BUY
opportunities with reasoning. Runs during/around Indian market hours (IST).
"""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import config
import llm
from embeddings import get_chroma_collection
from price_service import fetch_stock_price
from sentiment import compute_sentiment

OPPORTUNITIES_PATH = config.DB_PATH / "opportunities.json"


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _ist_now() -> datetime:
    return datetime.now(UTC) + timedelta(hours=5, minutes=30)


def is_market_hours() -> bool:
    now = _ist_now()
    return now.weekday() < 5 and \
        now.replace(hour=9, minute=15, second=0, microsecond=0) <= now <= \
        now.replace(hour=15, minute=30, second=0, microsecond=0)


def should_run_scanner() -> tuple[bool, str]:
    now = _ist_now()
    if now.weekday() >= 5:
        return False, "weekend"
    if (now.hour == 8 and now.minute >= 30) or (now.hour == 9 and now.minute < 15):
        return True, "pre_market"
    if is_market_hours():
        return True, "market_hours"
    if (now.hour == 15 and now.minute >= 30) or now.hour == 16:
        return True, "post_market"
    return False, "after_hours"


@dataclass
class Opportunity:
    ticker: str
    sentiment: float
    news_count: int
    headlines: list[str]
    reasoning: str
    confidence: float
    scan_type: str
    scanned_at: str
    current_price: float | None = None
    price_change: float | None = None
    price_change_percent: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScanResult:
    success: bool
    scan_type: str
    candidates_found: int
    opportunities: list[Opportunity]
    scanned_at: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"success": self.success, "scan_type": self.scan_type,
                "candidates_found": self.candidates_found,
                "opportunities": [o.to_dict() for o in self.opportunities],
                "scanned_at": self.scanned_at, "message": self.message}


class OpportunityScanner:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_scan: ScanResult | None = None
        self._opportunities: list[Opportunity] = []
        self._load()

    def _load(self) -> None:
        if OPPORTUNITIES_PATH.exists():
            try:
                data = json.loads(OPPORTUNITIES_PATH.read_text(encoding="utf-8"))
                self._opportunities = [Opportunity(**o) for o in data.get("opportunities", [])]
            except Exception:
                self._opportunities = []

    def _save(self) -> None:
        try:
            OPPORTUNITIES_PATH.parent.mkdir(parents=True, exist_ok=True)
            OPPORTUNITIES_PATH.write_text(json.dumps(
                {"opportunities": [o.to_dict() for o in self._opportunities],
                 "updated_at": _utcnow_iso()}, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _recent_news_by_ticker(self) -> dict[str, list[dict[str, str]]]:
        try:
            collection = get_chroma_collection()
        except Exception:
            return {}
        cutoff = (datetime.now(UTC) - timedelta(hours=config.SCANNER_LOOKBACK_HOURS)).isoformat()
        total = collection.count()
        if total == 0:
            return {}
        grouped: dict[str, list[dict[str, str]]] = {}
        offset = 0
        while offset < total:
            result = collection.get(limit=500, offset=offset,
                                    include=["metadatas"])
            ids = result.get("ids", []) or []
            metadatas = result.get("metadatas", []) or []
            if not ids:
                break
            for idx, _ in enumerate(ids):
                metadata = metadatas[idx] if idx < len(metadatas) and isinstance(metadatas[idx], dict) else {}
                seen_at = metadata.get("ingested_at", "") or metadata.get("published_at", "")
                if seen_at and seen_at < cutoff:
                    continue
                tags = str(metadata.get("ticker_tags", "") or "")
                if not tags:
                    continue
                title = metadata.get("Title", "") or metadata.get("title", "") or ""
                description = metadata.get("Description", "") or metadata.get("description", "") or ""
                date = metadata.get("published_at", "") or seen_at
                for ticker in [t.strip().upper() for t in tags.split(",") if t.strip()]:
                    grouped.setdefault(ticker, []).append(
                        {"title": title, "description": description, "date": date})
            offset += len(ids)
        return grouped

    def _filter_candidates(self) -> list[dict[str, Any]]:
        grouped = self._recent_news_by_ticker()
        candidates = []
        for ticker, items in grouped.items():
            # Score each article on its own and average — scoring the blob
            # saturates at exactly 1.0 whenever every matched term is
            # positive, which makes every candidate tie.
            scores = [compute_sentiment(f"{i['title']} {i['description']}")
                      for i in items]
            sentiment = sum(scores) / len(scores) if scores else 0.0
            if sentiment > config.SCANNER_SENTIMENT_THRESHOLD:
                candidates.append({
                    "ticker": ticker, "sentiment": sentiment,
                    "news_count": len(items),
                    "headlines": [i["title"] for i in items[:5]],
                })
        candidates.sort(key=lambda c: c["sentiment"], reverse=True)
        return candidates[:config.SCANNER_MAX_CANDIDATES]

    def _select_with_llm(self, candidates: list[dict[str, Any]],
                         scan_type: str) -> list[Opportunity]:
        if not candidates:
            return []
        context = {
            "pre_market": "This is a PRE-MARKET scan (8:30 AM). Focus on stocks that could move at market open.",
            "market_hours": "This is during MARKET HOURS. Focus on immediate actionable opportunities.",
            "post_market": "This is a POST-MARKET scan. Identify stocks to watch for tomorrow.",
        }
        lines = ""
        for idx, c in enumerate(candidates, 1):
            lines += (f"{idx}. {c['ticker']} (sentiment: {c['sentiment']:.2f}, "
                      f"{c['news_count']} articles)\n   Headlines: "
                      f"{'; '.join(c['headlines'][:3])}\n\n")
        prompt = (
            f"You are a stock market analyst. Analyze these {len(candidates)} stocks "
            f"with positive news sentiment and select the TOP "
            f"{config.SCANNER_TOP_OPPORTUNITIES} best BUY opportunities.\n\n"
            f"{context.get(scan_type, '')}\n\nCANDIDATES:\n{lines}\n"
            "For each selection, consider:\n1. News strength and momentum\n"
            "2. Sector diversification (avoid picking too many from same sector)\n"
            "3. Confidence level based on news quality\n\n"
            "Return ONLY valid JSON array (no markdown):\n"
            '[{"ticker": "SYMBOL", "reasoning": "brief 1-2 sentence reason", '
            '"confidence": 0.0-1.0}, ...]\n\n'
            f"Pick exactly {config.SCANNER_TOP_OPPORTUNITIES} stocks, ordered by "
            "confidence (highest first)."
        )
        try:
            # 5 picks with reasoning is ~500 tokens; 1024 truncates mid-JSON
            # when the prompt holds 20 candidates, so give it room.
            selections = llm.parse_json_array(
                llm.generate(prompt, temperature=0.3, max_tokens=2048)) or []
            by_ticker = {c["ticker"]: c for c in candidates}
            opportunities = []
            for sel in selections[:config.SCANNER_TOP_OPPORTUNITIES]:
                ticker = str(sel.get("ticker", "")).upper()
                if ticker not in by_ticker:
                    continue
                c = by_ticker[ticker]
                price = fetch_stock_price(ticker)
                opportunities.append(Opportunity(
                    ticker=ticker, sentiment=c["sentiment"], news_count=c["news_count"],
                    headlines=c["headlines"], reasoning=sel.get("reasoning", ""),
                    confidence=float(sel.get("confidence", 0.7) or 0.7),
                    scan_type=scan_type, scanned_at=_utcnow_iso(), **price))
            if opportunities:
                return opportunities
        except Exception:
            pass
        # Fallback: top by sentiment, no LLM.
        out = []
        for c in candidates[:config.SCANNER_TOP_OPPORTUNITIES]:
            price = fetch_stock_price(c["ticker"])
            out.append(Opportunity(
                ticker=c["ticker"], sentiment=c["sentiment"], news_count=c["news_count"],
                headlines=c["headlines"], reasoning="High positive sentiment in recent news",
                confidence=min(0.5 + c["sentiment"], 0.9),
                scan_type=scan_type, scanned_at=_utcnow_iso(), **price))
        return out

    def scan(self, scan_type: str = "market_hours") -> ScanResult:
        with self._lock:
            scanned_at = _utcnow_iso()
            if not config.SCANNER_ENABLED:
                return ScanResult(False, scan_type, 0, [], scanned_at, "Scanner is disabled")
            try:
                candidates = self._filter_candidates()
                if not candidates:
                    result = ScanResult(True, scan_type, 0, [], scanned_at,
                                        "No positive candidates found")
                    self._last_scan = result
                    return result
                opportunities = self._select_with_llm(candidates, scan_type)
                self._opportunities = opportunities
                self._save()
                result = ScanResult(True, scan_type, len(candidates), opportunities,
                                    scanned_at,
                                    f"Found {len(opportunities)} opportunities from "
                                    f"{len(candidates)} candidates")
                self._last_scan = result
                return result
            except Exception as exc:
                return ScanResult(False, scan_type, 0, [], scanned_at, str(exc))

    def get_opportunities(self) -> list[dict[str, Any]]:
        with self._lock:
            return [o.to_dict() for o in self._opportunities]

    def get_status(self) -> dict[str, Any]:
        should_run, reason = should_run_scanner()
        return {
            "enabled": config.SCANNER_ENABLED,
            "sentiment_threshold": config.SCANNER_SENTIMENT_THRESHOLD,
            "max_candidates": config.SCANNER_MAX_CANDIDATES,
            "top_opportunities": config.SCANNER_TOP_OPPORTUNITIES,
            "lookback_hours": config.SCANNER_LOOKBACK_HOURS,
            "is_market_hours": is_market_hours(),
            "should_run_now": should_run,
            "current_mode": reason,
            "last_scan": self._last_scan.to_dict() if self._last_scan else None,
            "opportunities_count": len(self._opportunities),
        }


opportunity_scanner = OpportunityScanner()
