"""Live news ingestion — RSS (free) + NewsAPI / Finnhub (optional keys).

Runs on a schedule from main.py. Articles are ticker-tagged from the alias
table, embedded locally, and stored in ChromaDB with deterministic IDs, so
re-runs are idempotent. Also ships the historical CSV importer.
"""
from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import requests

import config
from embeddings import (
    build_document_id,
    build_document_text,
    embed_texts,
    get_chroma_collection,
)
from stock_data import SECTOR_QUERIES, STOCK_ALIASES

INDIA_NEWS_DOMAINS: list[str] = [
    "economictimes.indiatimes.com", "moneycontrol.com", "livemint.com",
    "business-standard.com", "thehindubusinessline.com", "financialexpress.com",
    "ndtvprofit.com", "zeebiz.com", "cnbctv18.com", "businesstoday.in",
]

INDIA_RSS_FEEDS: list[tuple[str, str]] = [
    ("ET Markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("ET Stocks", "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"),
    ("Moneycontrol News", "https://www.moneycontrol.com/rss/marketreports.xml"),
    ("Moneycontrol Stocks", "https://www.moneycontrol.com/rss/results.xml"),
    ("Business Standard Markets", "https://www.business-standard.com/rss/markets-106.rss"),
    ("Livemint Markets", "https://www.livemint.com/rss/markets"),
    ("Hindu BL Markets", "https://www.thehindubusinessline.com/markets/feeder/default.rss"),
    ("NDTV Profit", "https://feeds.feedburner.com/ndtvprofit-latest"),
]

STATE_PATH = config.DB_PATH / "live_ingest_state.json"
USER_AGENT = "Mozilla/5.0 (compatible; AI-Investment-Intelligence-Platform/1.0)"


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _safe(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (value or "").lower()).strip()


def _contains(haystack: str, alias: str) -> bool:
    alias = _norm(alias)
    if not alias:
        return False
    if " " in alias:
        return alias in haystack
    return re.search(rf"\b{re.escape(alias)}\b", haystack) is not None


def detect_ticker_tags(title: str, description: str) -> list[str]:
    """Tag an article with the tickers it is actually about.

    Company-name aliases match case-insensitively on normalised text, but
    the bare symbol only matches as an ALL-CAPS token in the original text:
    tickers are written in caps (RELIANCE, TCS), while a symbol that is also
    an English word (PERSISTENT, AMBER, ESCORTS) must not match its lowercase
    use — "persistent inflation" is not Persistent Systems.
    """
    raw = f"{title or ''} {description or ''}"
    haystack = _norm(raw)
    if not haystack:
        return []
    found: list[str] = []
    for symbol, aliases in STOCK_ALIASES.items():
        symbol_as_token = re.search(rf"\b{re.escape(symbol)}\b", raw) is not None
        if symbol_as_token or any(_contains(haystack, a) for a in aliases):
            found.append(symbol)
    return sorted(set(found))


def _parse_iso(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


@dataclass
class IngestSummary:
    provider: str
    fetched: int
    candidate: int
    inserted: int
    skipped_existing: int
    failed: bool
    message: str
    run_started_at: str
    run_finished_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider, "fetched": self.fetched,
            "candidate": self.candidate, "inserted": self.inserted,
            "skipped_existing": self.skipped_existing, "failed": self.failed,
            "message": self.message, "run_started_at": self.run_started_at,
            "run_finished_at": self.run_finished_at,
        }


class LiveNewsIngestor:
    def __init__(self) -> None:
        self.enabled = config.LIVE_NEWS_ENABLED
        self.providers = config.LIVE_NEWS_PROVIDERS
        self.provider = self.providers[0]
        self.interval_minutes = config.LIVE_NEWS_INTERVAL_MINUTES
        self.lookback_hours = config.LIVE_NEWS_LOOKBACK_HOURS
        self.page_size = config.LIVE_NEWS_PAGE_SIZE
        self.max_articles = config.LIVE_NEWS_MAX_ARTICLES
        self.use_sector_rotation = config.USE_SECTOR_ROTATION
        self.use_india_domains = config.USE_INDIA_DOMAINS
        self.rss_enabled = config.RSS_ENABLED
        self._lock = threading.Lock()
        self._state = self._load_state()
        self._collection = get_chroma_collection()

    # ── state ──
    def _load_state(self) -> dict[str, Any]:
        default = {"last_successful_ingest_at": None, "last_status": "never_run",
                   "last_summary": None, "sector_index": 0}
        if not STATE_PATH.exists():
            return default
        try:
            raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            return {**default, **raw} if isinstance(raw, dict) else default
        except Exception:
            return {**default, "last_status": "state_read_error"}

    def _save_state(self) -> None:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(self._state, ensure_ascii=False, indent=2),
                              encoding="utf-8")

    def _resolve_from_dt(self) -> datetime:
        now = datetime.now(UTC)
        fallback = now - timedelta(hours=self.lookback_hours)
        since = _parse_iso(_safe(self._state.get("last_successful_ingest_at", "")))
        return fallback if since is None or since > now else since

    def _sector_query(self) -> str:
        if not self.use_sector_rotation or not SECTOR_QUERIES:
            return config.NEWS_QUERY
        return SECTOR_QUERIES[self._state.get("sector_index", 0) % len(SECTOR_QUERIES)]

    # ── fetchers ──
    def _fetch_rss(self) -> list[dict[str, str]]:
        if not self.rss_enabled:
            return []
        from_dt = self._resolve_from_dt()
        parsed: list[dict[str, str]] = []
        for source_name, feed_url in INDIA_RSS_FEEDS:
            try:
                resp = requests.get(feed_url, timeout=15,
                                    headers={"User-Agent": USER_AGENT})
                if resp.status_code >= 400:
                    continue
                items = re.findall(r"<item[^>]*>(.*?)</item>", resp.text,
                                   flags=re.DOTALL | re.IGNORECASE)
                for item_xml in items[:20]:
                    def tag(name: str) -> str:
                        m = re.search(rf"<{name}[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{name}>",
                                      item_xml, flags=re.DOTALL | re.IGNORECASE)
                        return _safe(m.group(1)) if m else ""
                    title, description = tag("title"), tag("description")
                    description = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", description)).strip()
                    url, pub = tag("link"), tag("pubDate")
                    published_at = ""
                    if pub:
                        try:
                            dt = parsedate_to_datetime(pub)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=UTC)
                            if dt < from_dt:
                                continue
                            published_at = dt.isoformat()
                        except Exception:
                            pass
                    if not title or len(title) < 10 or len(description or title) < 20:
                        continue
                    parsed.append({"title": title, "description": description or title,
                                   "published_at": published_at, "url": url,
                                   "source": source_name, "provider": "rss"})
                    if len(parsed) >= self.max_articles:
                        return parsed[:self.max_articles]
            except Exception:
                continue
            if len(parsed) >= self.max_articles:
                break
        return parsed[:self.max_articles]

    def _fetch_newsapi(self) -> list[dict[str, str]]:
        if not config.NEWSAPI_KEY:
            raise RuntimeError("NEWSAPI_KEY is not configured.")
        from_dt = self._resolve_from_dt()
        params: dict[str, Any] = {
            "q": self._sector_query(),
            "from": from_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "language": "en", "sortBy": "publishedAt", "pageSize": self.page_size,
        }
        if self.use_india_domains:
            params["domains"] = ",".join(INDIA_NEWS_DOMAINS[:10])
        resp = requests.get("https://newsapi.org/v2/everything",
                            headers={"X-Api-Key": config.NEWSAPI_KEY},
                            params=params, timeout=30)
        if resp.status_code >= 400:
            raise RuntimeError(f"NewsAPI request failed: {resp.status_code} {resp.text[:400]}")
        payload = resp.json()
        if payload.get("status") != "ok":
            raise RuntimeError(f"NewsAPI returned non-ok status: {payload}")
        self._state["sector_index"] = (self._state.get("sector_index", 0) + 1) % len(SECTOR_QUERIES)
        out: list[dict[str, str]] = []
        for item in payload.get("articles", [])[:self.max_articles]:
            title = _safe(item.get("title"))
            description = _safe(item.get("description")) or _safe(item.get("content"))
            if not title or len(description) < 20:
                continue
            out.append({"title": title, "description": description,
                        "published_at": _safe(item.get("publishedAt")),
                        "url": _safe(item.get("url")),
                        "source": _safe((item.get("source") or {}).get("name"))})
        return out

    def _fetch_finnhub(self) -> list[dict[str, str]]:
        if not config.FINNHUB_API_KEY:
            raise RuntimeError("FINNHUB_API_KEY is not configured.")
        from_dt = self._resolve_from_dt()
        resp = requests.get("https://finnhub.io/api/v1/news",
                            params={"category": config.FINNHUB_NEWS_CATEGORY,
                                    "token": config.FINNHUB_API_KEY}, timeout=30)
        if resp.status_code >= 400:
            raise RuntimeError(f"Finnhub request failed: {resp.status_code} {resp.text[:400]}")
        payload = resp.json()
        if not isinstance(payload, list):
            raise RuntimeError(f"Finnhub returned unexpected payload: {payload}")
        out: list[dict[str, str]] = []
        for item in payload[:self.max_articles]:
            title = _safe(item.get("headline"))
            description = _safe(item.get("summary"))
            raw_dt = item.get("datetime")
            published_at = datetime.fromtimestamp(float(raw_dt), tz=UTC).isoformat().replace("+00:00", "Z") \
                if isinstance(raw_dt, (int, float)) else ""
            parsed_dt = _parse_iso(published_at)
            if parsed_dt is not None and parsed_dt < from_dt:
                continue
            if not title or len(description) < 20:
                continue
            out.append({"title": title, "description": description,
                        "published_at": published_at, "url": _safe(item.get("url")),
                        "source": _safe(item.get("source")), "provider": "finnhub"})
        return out

    def _fetch_articles(self) -> tuple[str, list[dict[str, str]]]:
        errors: list[str] = []
        articles: list[dict[str, str]] = []
        primary = ""
        if "rss" in self.providers:
            try:
                articles.extend(self._fetch_rss())
            except Exception as exc:
                errors.append(f"rss: {exc}")
        for name in [p for p in self.providers if p != "rss"]:
            try:
                fetched = self._fetch_newsapi() if name == "newsapi" else \
                    self._fetch_finnhub() if name == "finnhub" else \
                    (_ for _ in ()).throw(RuntimeError(f"Unsupported provider '{name}'"))
                articles.extend({**a, "provider": _safe(a.get("provider") or name)}
                                for a in fetched)
                primary = name
                break
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        if articles:
            return primary or "rss", articles
        raise RuntimeError("All live news providers failed. " + " | ".join(errors))

    # ── store ──
    def _existing_ids(self, ids: list[str]) -> set[str]:
        existing: set[str] = set()
        for start in range(0, len(set(ids)), 100):
            batch = list(set(ids))[start:start + 100]
            try:
                for found in self._collection.get(ids=batch, include=[]).get("ids", []) or []:
                    existing.add(str(found))
            except Exception:
                for single in batch:
                    try:
                        if self._collection.get(ids=[single], include=[]).get("ids"):
                            existing.add(single)
                    except Exception:
                        pass
        return existing

    def _metadata(self, article: dict[str, Any]) -> dict[str, Any]:
        published_at = _safe(article.get("published_at"))
        tags = article.get("ticker_tags", [])
        tags_csv = ",".join(_safe(t).upper() for t in tags) if isinstance(tags, list) else ""
        return {
            "Date": published_at.split("T", 1)[0] if "T" in published_at else published_at,
            "Title": _safe(article.get("title")),
            "Description": _safe(article.get("description")),
            "published_at": published_at,
            "source": _safe(article.get("source")),
            "url": _safe(article.get("url")),
            "ingested_at": _utcnow_iso(),
            "provider": _safe(article.get("provider") or self.provider),
            "ticker_tags": tags_csv,
            "primary_ticker": tags_csv.split(",", 1)[0] if tags_csv else "",
        }

    def ingest_once(self) -> IngestSummary:
        started = _utcnow_iso()
        with self._lock:
            if not self.enabled:
                summary = IngestSummary(self.provider, 0, 0, 0, 0, True,
                                        "LIVE_NEWS_ENABLED is false.", started, _utcnow_iso())
                self._state.update(last_status="disabled", last_summary=summary.to_dict())
                self._save_state()
                return summary
            try:
                provider, fetched = self._fetch_articles()
                ids = [build_document_id("live", _safe(a.get("title")),
                                         _safe(a.get("published_at")), _safe(a.get("url")))
                       for a in fetched]
                existing = self._existing_ids(ids)
                candidates, seen, skipped = [], set(), 0
                for idx, article in enumerate(fetched):
                    if ids[idx] in existing or ids[idx] in seen:
                        skipped += 1
                        continue
                    seen.add(ids[idx])
                    candidates.append((ids[idx], article))
                if not candidates:
                    summary = IngestSummary(provider, len(fetched), 0, 0, skipped, False,
                                            "No new articles to ingest.", started, _utcnow_iso())
                    self._state.update(last_status="ok",
                                       last_successful_ingest_at=_utcnow_iso(),
                                       last_summary=summary.to_dict())
                    self._save_state()
                    return summary
                docs, metas, doc_ids = [], [], []
                for doc_id, article in candidates:
                    tags = detect_ticker_tags(_safe(article.get("title")),
                                              _safe(article.get("description")))
                    article["ticker_tags"] = tags
                    doc_ids.append(doc_id)
                    docs.append(build_document_text(_safe(article.get("title")),
                                                   _safe(article.get("description")), tags))
                    metas.append(self._metadata(article))
                self._collection.add(ids=doc_ids, documents=docs,
                                     embeddings=embed_texts(docs), metadatas=metas)
                summary = IngestSummary(provider, len(fetched), len(candidates),
                                        len(doc_ids), skipped, False,
                                        "Live news ingestion completed.", started, _utcnow_iso())
                self._state.update(last_status="ok",
                                   last_successful_ingest_at=_utcnow_iso(),
                                   last_summary=summary.to_dict())
                self._save_state()
                return summary
            except Exception as exc:
                summary = IngestSummary(self.provider, 0, 0, 0, 0, True, str(exc),
                                        started, _utcnow_iso())
                self._state.update(last_status="error", last_summary=summary.to_dict())
                self._save_state()
                return summary

    def get_status(self) -> dict[str, Any]:
        idx = self._state.get("sector_index", 0)
        return {
            "enabled": self.enabled, "provider": self.provider,
            "providers": self.providers, "interval_minutes": self.interval_minutes,
            "lookback_hours": self.lookback_hours, "page_size": self.page_size,
            "max_articles_per_run": self.max_articles,
            "last_successful_ingest_at": self._state.get("last_successful_ingest_at"),
            "last_status": self._state.get("last_status"),
            "last_summary": self._state.get("last_summary"),
            "sector_rotation_enabled": self.use_sector_rotation,
            "sector_index": idx, "total_sectors": len(SECTOR_QUERIES),
            "current_sector_query": SECTOR_QUERIES[idx % len(SECTOR_QUERIES)]
            if self.use_sector_rotation and SECTOR_QUERIES else "",
            "india_domains_enabled": self.use_india_domains,
            "rss_enabled": self.rss_enabled, "rss_feeds_count": len(INDIA_RSS_FEEDS),
        }

    def retag_existing_records(self, batch_size: int = 200) -> dict[str, Any]:
        started = _utcnow_iso()
        processed = updated = tagged = untagged = 0
        with self._lock:
            try:
                total = int(self._collection.count())
                offset = 0
                while offset < total:
                    resp = self._collection.get(limit=batch_size, offset=offset,
                                                include=["documents", "metadatas"])
                    ids = resp.get("ids", []) or []
                    documents = resp.get("documents", []) or []
                    metadatas = resp.get("metadatas", []) or []
                    if not ids:
                        break
                    update_ids, update_metas = [], []
                    for idx, doc_id in enumerate(ids):
                        metadata = dict(metadatas[idx]) if idx < len(metadatas) and isinstance(metadatas[idx], dict) else {}
                        document = str(documents[idx]) if idx < len(documents) else ""
                        title = _safe(metadata.get("Title")) or _extract_field(document, "Title")
                        description = _safe(metadata.get("Description")) or _extract_field(document, "Description")
                        tags = detect_ticker_tags(title, description)
                        tagged += 1 if tags else 0
                        untagged += 0 if tags else 1
                        tags_csv = ",".join(tags)
                        primary = tags[0] if tags else ""
                        if tags_csv != _safe(metadata.get("ticker_tags")) or primary != _safe(metadata.get("primary_ticker")):
                            metadata["ticker_tags"] = tags_csv
                            metadata["primary_ticker"] = primary
                            update_ids.append(str(doc_id))
                            update_metas.append(metadata)
                    if update_ids:
                        self._collection.update(ids=update_ids, metadatas=update_metas)
                        updated += len(update_ids)
                    processed += len(ids)
                    offset += len(ids)
                return {"failed": False, "message": "Retag completed.",
                        "processed": processed, "updated": updated,
                        "tagged": tagged, "untagged": untagged,
                        "run_started_at": started, "run_finished_at": _utcnow_iso()}
            except Exception as exc:
                return {"failed": True, "message": str(exc), "processed": processed,
                        "updated": updated, "tagged": tagged, "untagged": untagged,
                        "run_started_at": started, "run_finished_at": _utcnow_iso()}


def _extract_field(document: str, field: str) -> str:
    m = re.search(rf"^{field}:\s*(.*)$", document or "",
                  flags=re.IGNORECASE | re.MULTILINE)
    return _safe(m.group(1)) if m else ""


# ─── Historical CSV import ───────────────────────────────────────────────────

def ingest_csv(csv_path: str | Path, batch_size: int = 100) -> dict[str, Any]:
    """Import a Date,Title,Description CSV into the vector store.

    Idempotent (deterministic IDs), resumable (state file), skips rows with
    short descriptions. The reference dataset is not shipped; any CSV with
    these columns works, including the seed file in data/.
    """
    import pandas as pd

    path = Path(csv_path)
    state_path = config.DB_PATH / "historical_ingest_state.json"
    state: dict[str, Any] = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            state = {}
    processed = int(state.get("processed", 0))
    collection = get_chroma_collection()
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [str(c).strip() for c in df.columns]
    for col in ("Date", "Title", "Description"):
        df[col] = df[col].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    df = df[df["Description"].str.len() >= 40]
    df = df[df["Title"].str.len() > 0]
    df = df[df["Date"].str.len() > 0]
    df = df.drop_duplicates(subset=["Date", "Title", "Description"], keep="first").reset_index(drop=True)

    inserted = skipped = 0
    total = len(df)
    for start in range(processed, total, batch_size):
        batch = df.iloc[start:start + batch_size]
        ids, docs, metas = [], [], []
        for _, row in batch.iterrows():
            title, description, date = row["Title"], row["Description"], row["Date"]
            doc_id = build_document_id("csv", title, date)
            ids.append(doc_id)
            tags = detect_ticker_tags(title, description)
            docs.append(build_document_text(title, description, tags))
            metas.append({"Date": date, "Title": title, "Description": description,
                          "published_at": date, "source": "historical_csv",
                          "url": "", "ingested_at": _utcnow_iso(),
                          "provider": "csv", "ticker_tags": ",".join(tags),
                          "primary_ticker": tags[0] if tags else ""})
        existing = set()
        try:
            existing = {str(i) for i in collection.get(ids=list(set(ids)), include=[]).get("ids", [])}
        except Exception:
            pass
        new_idx = [i for i, doc_id in enumerate(ids) if doc_id not in existing]
        skipped += len(ids) - len(new_idx)
        if new_idx:
            collection.add(ids=[ids[i] for i in new_idx],
                           documents=[docs[i] for i in new_idx],
                           embeddings=embed_texts([docs[i] for i in new_idx]),
                           metadatas=[metas[i] for i in new_idx])
            inserted += len(new_idx)
        processed = start + len(batch)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps({"processed": processed, "total": total}),
                              encoding="utf-8")
    return {"inserted": inserted, "skipped_existing": skipped, "total_rows": total,
            "collection_count": collection.count()}
