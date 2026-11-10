"""Live prices via Yahoo Finance, with a short cache.

NSE (.NS) first, BSE (.BO) as fallback. A failure is cached briefly so a
flapping quote service doesn't stall every request.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import yfinance as yf

from stock_data import PEER_GROUPS

PRICE_CACHE_TTL_SECONDS = 300
FAIL_CACHE_TTL_SECONDS = 15

_cache: dict[str, tuple[float, dict[str, float | None]]] = {}


def fetch_stock_price(ticker: str) -> dict[str, float | None]:
    if not ticker or ticker.upper() == "MARKET":
        return {"current_price": None, "price_change": None,
                "price_change_percent": None}

    symbol = ticker.upper().strip()
    if symbol in _cache:
        cached_at, data = _cache[symbol]
        ttl = FAIL_CACHE_TTL_SECONDS if data.get("current_price") is None \
            else PRICE_CACHE_TTL_SECONDS
        if time.time() - cached_at < ttl:
            return data

    for suffix in (".NS", ".BO"):
        try:
            info = yf.Ticker(f"{symbol}{suffix}").info
            current = info.get("currentPrice") or info.get("regularMarketPrice")
            if current is None:
                continue
            prev = info.get("previousClose") or info.get("regularMarketPreviousClose")
            change = round(current - prev, 2) if prev and prev > 0 else None
            change_pct = round(change / prev * 100, 2) if change is not None else None
            result = {"current_price": round(current, 2),
                      "price_change": change, "price_change_percent": change_pct}
            _cache[symbol] = (time.time(), result)
            return result
        except Exception:
            continue

    empty = {"current_price": None, "price_change": None,
             "price_change_percent": None}
    _cache[symbol] = (time.time(), empty)
    return empty


def fetch_peer_comparison(ticker: str, limit: int = 2) -> list[dict[str, Any]]:
    """Prices for up to `limit` peers, fetched in parallel."""
    peers = PEER_GROUPS.get(ticker.upper().strip(), [])
    if not peers:
        return []
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=limit) as pool:
        futures = {pool.submit(fetch_stock_price, p): p for p in peers[:limit]}
        for future in as_completed(futures, timeout=10):
            peer = futures[future]
            try:
                data = future.result(timeout=5)
            except Exception:
                data = {"current_price": None, "price_change": None,
                        "price_change_percent": None}
            results.append({"ticker": peer, **data})
    return results
