# AI Investment Intelligence Platform — Spec

AI investment-research platform for Indian equities (NSE/BSE). All code
written fresh for this repo.

## Product

A retail investor opens the app, types an NSE ticker (e.g. RELIANCE, TCS,
HDFCBANK), and gets: live price, news-driven sentiment with a BUY/HOLD/SELL
call, the drivers behind it, peer comparison, an AI summary, and the news
headlines it is based on. A Discover tab surfaces the day's best opportunities
from a scheduled scanner. A Portfolio tab tracks goal-based holdings with P&L
and AI suggestions. A Chat tab answers research questions with live data.

## Backend (FastAPI, Python 3.13)

### API contract (must stay stable — the frontend depends on it)

- `GET /` — name, version, status, endpoint list.
- `POST /analyze` `{ticker}` → ticker, query, sentiment, now_sentiment,
  pattern_sentiment, confidence, recent_news_count, pattern_news_count,
  latest_news_date, stale_data, stale_reason, explanation,
  positive_drivers[], negative_drivers[], news_references[{date,title}],
  recommendation (BUY|HOLD|SELL), current_price, price_change,
  price_change_percent, ai_summary, peers[]. Rate-limited (10/min/IP
  default, env-tunable). Ticker must be ≥3 chars.
- `GET /opportunities` → `{opportunities[], is_market_hours}`.
- `GET /opportunities/status` → scanner config + last scan.
- `POST /opportunities/scan` → runs a scan now, returns ScanResult.
- `POST /chat` `{message, session_id, context_data?}` → assistant message
  `{role, content, timestamp, data?}`.
- `GET /chat/history/{session_id}` → session messages.
- `POST /portfolio/analyze` `{goals[]}` → per-goal P&L + totals.
- `POST /portfolio/suggest` `{goal}` → `{goalId, suggestion,
  recommended_stocks[]}`.
- `POST /storage/portfolio/save`, `GET /storage/portfolio/load?user_id=`,
  `POST /storage/chat/save`, `GET /storage/chat/load?session_id=` — JSON
  file persistence.
- `GET /admin/live-news/status`, `POST /admin/live-news/refresh`,
  `POST /admin/live-news/retag-existing` — behind `X-Admin-Key` when
  `ADMIN_API_KEY` is set (open in dev when unset).
- Global JSON error handler; CORS allow-list via `ALLOWED_ORIGINS`
  (localhost regex by default, `*` for cloud).

### Analysis pipeline (fast path, default)

1. Extract ticker + search phrase from the query (`ON <TICKER>` or last
   all-caps token; fallback `MARKET`).
2. Retrieve candidate news: (a) ChromaDB semantic store, restricted to the
   last `FAST_NEWS_MAX_AGE_DAYS` (30) days, ranked by ticker-term match
   (ticker-tag hit +6, text hit +5) then recency; (b) local CSV rows, same
   ranking (ticker hit +5); (c) if no recent news, on-demand NewsAPI lookup
   (needs `NEWSAPI_KEY`, 30-day window, ticker terms, India context).
3. Dedupe by normalised title (first 12 tokens, numbers stripped) + date.
4. Split into recent (≤30d, max 5) and historical (max 5); pattern set =
   recent + historical.
5. Sentiment: `now` = mean of per-article scores over recent rows;
   `pattern` = time-decay-weighted mean over pattern rows; combined =
   `0.7*now + 0.3*pattern` when recent rows exist, else `pattern*0.35`.
   Clamp to [-1, 1].
6. Decision: no recent rows → HOLD; sentiment ≥ 0.20 → BUY; ≤ -0.20 → SELL;
   else HOLD.
7. Enrich in parallel: live price (yfinance), AI summary (LLM, headlines),
   peers (price for up to 2 peers).

### Sentiment engine (rule-based, explainable)

- Lexicon: positive terms (gain .9, surge 1.5, profit 1.1, growth 1.0,
  bullish 1.2, record 1.2, …) and negative terms (fall .9, slump 1.4,
  loss 1.2, plunge 1.7, downgrade 1.2, …).
- Intensifiers multiply the term weight (slight .7, solid 1.1, sharp 1.3,
  significant 1.35, massive 1.6, extreme 1.7, …) — look back 3 tokens.
- Negation in the 3-token window flips the sign (no, not, never, without,
  hardly, barely).
- Contrast split (`but/however/despite/although/though/yet`): score each
  segment separately; the last segment gets a 1.2× recency boost.
- Numeric magnitude: a `%` figure in the text scales the score (≥10% → 1.15,
  ≥20% → 1.25, ≥50% → 1.4, ≥100% → 1.6).
- Per-article score = weighted sum / total absolute weight, clamped [-1, 1].
- Time decay for pattern weighting: ≤7d → 1.0, ≤90d → 0.6, ≤365d → 0.3,
  older → 0.15, multiplied by source quality (Reuters/Bloomberg 1.15,
  ET 1.12, Moneycontrol/Livemint/BusinessLine/Mint 1.08, CNBC 1.07,
  historical CSV 0.9, default 1.0). Unparseable date → 0.15.
- Confidence = 0.7·min(recent/5, 1) + 0.3·min(pattern/40, 1).
- Drivers: top 3 positive and top 3 negative headlines by per-article score.
- Explanation: one sentence naming the recommendation, sentiment values,
  counts, and whether data is live-fetched, stale, or missing.

### Prices (yfinance)

- Try `TICKER.NS` then `TICKER.BO`. 5-minute cache (15s for failures).
  Price, change vs previous close, change %. `MARKET`/empty → nulls.
- Peers: per-ticker peer lists by sector; fetch up to 2 in parallel.

### Stock data (public facts)

- Ticker → company-name aliases (~200 NSE names, all major sectors).
- Peer groups by sector. Sector query list for ingestion rotation.
- Source quality weights (above). Ticker suffix splits (BANK, STEEL, …).
- Generic terms + query stopwords for matching.

### Embeddings + vector store

- Local Sentence Transformers `all-MiniLM-L6-v2` (384-dim, CPU), batch 64,
  normalised. ChromaDB persistent collection `market_news_v2`.
- Deterministic doc IDs: `news_<sha256(source|url|title|date)[:32]>`.
- Document text: `Title / Description / TickerTags`.
- Lazy model load (thread-safe singleton); ChromaDB client lazy too, so the
  API boots and serves even before any model download.

### Ingestion

- Live ingestion (background scheduler, every `LIVE_NEWS_INTERVAL_MINUTES`
  = 30): providers `newsapi,rss` (configurable). RSS is free and always
  attempted: 8 Indian business feeds (ET Markets/Stocks, Moneycontrol,
  Business Standard, Livemint, Hindu BusinessLine, NDTV Profit). NewsAPI
  (optional key) with India domains + rotating sector queries; Finnhub
  (optional key, `general` category). Dedupe by doc ID, ticker-tag each
  article from aliases, embed + store, persist state
  (`live_ingest_state.json`, sector index, last success).
- Historical CSV ingestion script: any `Date,Title,Description` CSV,
  normalised, deduped, min 40-char descriptions, batched, resumable,
  idempotent. The repo ships a small seed CSV of recent public RSS
  headlines, and the live RSS feed keeps the store fresh.
- Retag endpoint: re-detect ticker tags over the whole collection.

### Opportunity scanner (hybrid)

- Market-hours logic in IST: pre-market 08:30–09:15, market 09:15–15:30
  (Mon–Fri), post-market 15:30–17:00; otherwise idle.
- Step 1 (script): group last-48h news by ticker tag, score combined text,
  keep sentiment > 0.15, top 20 by sentiment.
- Step 2 (LLM): pick top 5 BUY with 1–2 sentence reasoning + confidence,
  sector-diversified. Fallback if the LLM fails: top 5 by sentiment with
  generic reasoning and confidence `min(0.5 + sentiment, 0.9)`.
- Persist to `opportunities.json`; status endpoint exposes config + last scan.

### Portfolio

- Goal: `{id, name, targetAmount, targetDate, riskTolerance, holdings[]}`;
  holding: `{ticker, quantity, buyPrice, buyDate}`.
- Per holding: live price → invested, current value, P&L, P&L % (price
  missing → value = invested, P&L 0). Per goal: totals, progress %
  (capped 100), years left. Portfolio totals across goals.
- Suggest: per-holding news sentiment (vector query), risk guidance
  (conservative/moderate/aggressive), LLM returns 2–3 suggestions + a
  `RECOMMENDED_STOCKS` JSON block (2–4 NSE picks, not already held, priced,
  sized to the remaining amount). LLM failure → rule-based fallback
  (negative sentiment flag, >40% concentration flag, else "balanced").

### Chat (research assistant)

- Two-step intent flow: LLM (temperature 0.3) returns an intent tag
  (`[ANALYZE:TICKER]`, `[COMPARE:A,B]`, `[WATCHLIST]`, `[PORTFOLIO]`,
  `[OPPORTUNITIES]`) or a direct answer. Data intents fetch live data via
  the existing pipeline, then a second LLM call (temperature 0.7) writes the
  conversational answer with the data woven in. Tags stripped from output.
- Portfolio context (goals + holdings) injected into the system prompt when
  supplied. Sessions in memory (last 20 messages), persisted via storage
  endpoints. `₹` for prices, concise (2–4 paragraphs).

### LLM providers (new in this build)

- Provider interface: `chat(messages, temperature, max_tokens)` returning
  text, plus `generate(prompt)` for single-shot JSON tasks.
- **Inception Labs (active now):** OpenAI-compatible client, base
  `https://api.inceptionlabs.ai/v1`, model `mercury-2.5` (260k context)
  default, key from `INCEPTION_API_KEY`. Verified live.
- **Gemini (supported):** `google-genai`, model `gemini-2.5-flash`, key
  from `GOOGLE_API_KEY`. Used as fallback for chat/summary/scanner and as
  the GenAI analysis path when `LLM_PROVIDER=gemini`.
- `LLM_PROVIDER` env selects the primary (`inception` default). Every LLM
  call tries primary, then falls back to the other provider when configured.
  No provider configured → the deterministic fast path still works; AI
  summary/suggestions degrade to the rule-based fallbacks (never a crash).
- Optional GenAI analysis path (`USE_GENAI_ANALYSIS=true`): LangGraph
  Scout (vector search, top 5) → Analyst+Advisor (one LLM call returning
  JSON sentiment/decision/explanation), with quota retry (4 attempts,
  backoff) and automatic fallback to the fast path on any failure.
- Keys live only in `.env` (gitignored, never committed).

## Frontend (Next.js 14, TypeScript, Tailwind, Recharts, Zustand)

- Routes: `/` (home), `/analyze`, `/discover`, `/portfolio`, `/chat`,
  `/settings`. Bottom nav on mobile, sidebar on desktop.
- Same API contract as above (client in `lib/api/`, normalisers per
  resource). `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).
- Design: completely new, built with the taste-skill (sharp radius,
  fintech). One system, one section per screen, real product UI (live data,
  not mockups), hero entrance + one or two dealt moments per page.
- Must show, at minimum: analyse (price card, sentiment gauge + trend,
  drivers, peers, AI summary, news references, stale-data states), discover
  (opportunity cards, scanner status, manual scan), portfolio (goals, P&L,
  progress, add goal/holding, AI suggestions), chat (bubbles, typing
  indicator, history, portfolio context), settings (API URL, provider
  status, data freshness).

## Quality bar (N11)

- Backend: pytest (sentiment unit tests with fixed expectations, ticker
  extraction, API smoke with mocked price/news/LLM), `ruff` clean.
- Frontend: `tsc --noEmit` + `next build` green.
- Docker: backend image (gunicorn/uvicorn, port 10000) + compose with
  frontend. CI: GitHub Actions (backend tests, frontend build).
- README (own words): what it is, architecture diagram, setup, env table,
  API table, screenshots, license (MIT).
- Real screenshots from a running stack (backend + frontend, live data).
- Banner (1200×630) for the repo social preview.
- Commits under Jaikishan Bagul <pronoob.dev@gmail.com> only.
