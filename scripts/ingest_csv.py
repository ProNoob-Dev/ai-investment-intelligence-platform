#!/usr/bin/env python3
"""Import a Date,Title,Description CSV into the vector store.

Usage:
    python scripts/ingest_csv.py data/seed_news.csv
    python scripts/ingest_csv.py path/to/IndianFinancialNews.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from ingest import ingest_csv  # noqa: E402


def main() -> int:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/seed_news.csv")
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return 1
    result = ingest_csv(csv_path)
    print(f"Inserted {result['inserted']} new articles "
          f"({result['skipped_existing']} already present, "
          f"{result['total_rows']} rows). "
          f"Collection now holds {result['collection_count']} documents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
