"""Scanner candidate scoring — per-article average must differentiate."""
from scanner import OpportunityScanner


def _grouped(monkeypatch, groups):
    scanner = OpportunityScanner()
    monkeypatch.setattr(scanner, "_recent_news_by_ticker", lambda: groups)
    return scanner


def test_blob_would_saturate_but_average_differentiates(monkeypatch):
    # Two tickers whose articles are all-positive in isolation: scoring the
    # concatenated blob returns exactly 1.0 for both. Per-article average
    # with one mixed article must separate them.
    groups = {
        "AAA": [
            {"title": "AAA surges 9% on strong profit", "description": "Profit beats estimates", "date": ""},
            {"title": "AAA drops 5% post Q2, but profit surges on strong growth", "description": "Brokerages stay positive on growth", "date": ""},
        ],
        "BBB": [
            {"title": "BBB surges 9% on strong profit", "description": "Profit beats estimates", "date": ""},
        ],
    }
    scanner = _grouped(monkeypatch, groups)
    candidates = {c["ticker"]: c for c in scanner._filter_candidates()}
    assert "AAA" in candidates and "BBB" in candidates
    assert candidates["AAA"]["sentiment"] < candidates["BBB"]["sentiment"]
    assert candidates["BBB"]["sentiment"] <= 1.0
