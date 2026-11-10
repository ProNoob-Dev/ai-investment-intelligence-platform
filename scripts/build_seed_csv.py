#!/usr/bin/env python3
"""Build data/seed_news.csv from the 8 live public RSS feeds.

One-off seed builder (not part of the app runtime). Fetches each feed,
keeps items with a usable description, and writes Date,Title,Description,Source
in ISO dates so the backend's parse_datetime_text handles them.
"""
from __future__ import annotations

import csv
import re
import subprocess
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

FEEDS: list[tuple[str, str]] = [
    ("ET Markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("ET Stocks", "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"),
    ("Moneycontrol News", "https://www.moneycontrol.com/rss/marketreports.xml"),
    ("Moneycontrol Stocks", "https://www.moneycontrol.com/rss/results.xml"),
    ("Business Standard Markets", "https://www.business-standard.com/rss/markets-106.rss"),
    ("Livemint Markets", "https://www.livemint.com/rss/markets"),
    ("Hindu BL Markets", "https://www.thehindubusinessline.com/markets/feeder/default.rss"),
    ("NDTV Profit", "https://feeds.feedburner.com/ndtvprofit-latest"),
]

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def iso_date(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        pass
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return ""


def fetch(url: str) -> bytes:
    """requests first; curl fallback (some feeds reject the VM's proxy path).

    A 200 with no <item> means a bot-check/empty page, not the feed — fall
    through to curl in that case too.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        if resp.content.strip() and b"<item" in resp.content:
            return resp.content
    except Exception:  # noqa: BLE001 - fall through to curl
        pass
    proc = subprocess.run(
        ["curl", "-s", "-m", "30", "-A", HEADERS["User-Agent"], url],
        capture_output=True, timeout=60, check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"curl failed for {url}")
    return proc.stdout


def main() -> int:
    out_path = Path(__file__).resolve().parent.parent / "data" / "seed_news.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for source, url in FEEDS:
        try:
            content = fetch(url)
        except Exception as exc:  # noqa: BLE001 - report and move on
            print(f"{source}: FAILED {exc}", file=sys.stderr)
            continue
        soup = BeautifulSoup(content, "xml")
        count = 0
        for item in soup.find_all("item"):
            title = clean(item.find("title").text if item.find("title") else "")
            desc = clean(item.find("description").text if item.find("description") else "")
            if not title or len(desc) < 40:
                continue
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            date = iso_date(item.find("pubDate").text if item.find("pubDate") else "")
            if not date:
                continue
            rows.append({"Date": date, "Title": title, "Description": desc, "Source": source})
            count += 1
        print(f"{source}: {count} items")

    rows.sort(key=lambda r: r["Date"], reverse=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Title", "Description", "Source"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
