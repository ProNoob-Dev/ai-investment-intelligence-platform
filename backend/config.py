"""Settings — one place for every env var. No extra dependency: os.getenv
helpers are enough for this. .env is loaded from the repo root, then the
backend directory (repo root wins for shared keys)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent

load_dotenv(ROOT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")


def _bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


# ─── LLM providers ──────────────────────────────────────────────────────────
# Inception Labs (Mercury, OpenAI-compatible) is the live provider now.
# Gemini is supported as a second provider / fallback.
LLM_PROVIDER = _str("LLM_PROVIDER", "inception").lower()
INCEPTION_API_KEY = _str("INCEPTION_API_KEY")
INCEPTION_BASE_URL = _str("INCEPTION_BASE_URL", "https://api.inceptionlabs.ai/v1")
INCEPTION_MODEL = _str("INCEPTION_MODEL", "mercury-3")
GOOGLE_API_KEY = _str("GOOGLE_API_KEY") or _str("GEMINI_API_KEY")
GEMINI_MODEL = _str("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_CHAT_MODEL = _str("GEMINI_CHAT_MODEL", "gemini-2.5-flash")

USE_GENAI_ANALYSIS = _bool("USE_GENAI_ANALYSIS", False)
ENABLE_AI_SUMMARY = _bool("ENABLE_AI_SUMMARY", True)

# ─── Data ───────────────────────────────────────────────────────────────────
DB_PATH = Path(
    _str("VECTOR_WEALTH_DB_PATH", str(BACKEND_DIR / "vector_wealth_db"))
)
CHROMA_COLLECTION_NAME = _str("CHROMA_COLLECTION_NAME", "market_news_v2")
EMBEDDING_MODEL = _str("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_DEVICE = _str("EMBEDDING_DEVICE", "cpu")
EMBEDDING_BATCH_SIZE = _int("EMBEDDING_BATCH_SIZE", 64)
NEWS_CSV_PATH = ROOT_DIR / "data" / "IndianFinancialNews.csv"
SEED_CSV_PATH = ROOT_DIR / "data" / "seed_news.csv"

# ─── Analysis tuning ────────────────────────────────────────────────────────
FAST_NEWS_MAX_AGE_DAYS = max(1, _int("FAST_NEWS_MAX_AGE_DAYS", 30))
FAST_NEWS_MAX_CANDIDATES = max(20, _int("FAST_NEWS_MAX_CANDIDATES", 120))
BUY_THRESHOLD = 0.20
SELL_THRESHOLD = -0.20

# ─── Live news ──────────────────────────────────────────────────────────────
LIVE_NEWS_ENABLED = _bool("LIVE_NEWS_ENABLED", True)
LIVE_NEWS_PROVIDERS = [
    p.strip().lower()
    for p in _str("LIVE_NEWS_PROVIDER", "newsapi,rss").split(",")
    if p.strip()
] or ["newsapi", "rss"]
NEWSAPI_KEY = _str("NEWSAPI_KEY")
FINNHUB_API_KEY = _str("FINNHUB_API_KEY")
FINNHUB_NEWS_CATEGORY = _str("FINNHUB_NEWS_CATEGORY", "general")
NEWS_QUERY = _str(
    "NEWS_QUERY",
    "Indian stock market OR NSE OR BSE OR Sensex OR Nifty OR earnings",
)
LIVE_NEWS_INTERVAL_MINUTES = max(5, _int("LIVE_NEWS_INTERVAL_MINUTES", 30))
LIVE_NEWS_LOOKBACK_HOURS = max(1, _int("LIVE_NEWS_LOOKBACK_HOURS", 24))
LIVE_NEWS_PAGE_SIZE = max(10, min(100, _int("LIVE_NEWS_PAGE_SIZE", 50)))
LIVE_NEWS_MAX_ARTICLES = max(10, _int("LIVE_NEWS_MAX_ARTICLES_PER_RUN", 100))
USE_SECTOR_ROTATION = _bool("USE_SECTOR_ROTATION", True)
USE_INDIA_DOMAINS = _bool("USE_INDIA_DOMAINS", True)
RSS_ENABLED = _bool("RSS_ENABLED", True)

# ─── Scanner ────────────────────────────────────────────────────────────────
SCANNER_ENABLED = _bool("SCANNER_ENABLED", True)
SCANNER_SENTIMENT_THRESHOLD = _float("SCANNER_SENTIMENT_THRESHOLD", 0.15)
SCANNER_MAX_CANDIDATES = _int("SCANNER_MAX_CANDIDATES", 20)
SCANNER_TOP_OPPORTUNITIES = _int("SCANNER_TOP_OPPORTUNITIES", 5)
SCANNER_LOOKBACK_HOURS = _int("SCANNER_LOOKBACK_HOURS", 48)

# ─── Server ─────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = _str("ALLOWED_ORIGINS", "")
ADMIN_API_KEY = _str("ADMIN_API_KEY")
RATE_LIMIT_MAX = _int("RATE_LIMIT_MAX", 10)
RATE_LIMIT_WINDOW_SECONDS = _int("RATE_LIMIT_WINDOW", 60)
DEBUG = _bool("DEBUG", False)
