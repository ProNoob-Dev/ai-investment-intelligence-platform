"""JSON file persistence for portfolios and chat history.

No database to run: files live next to the ChromaDB data, writes are atomic
(write temp, then rename) and guarded by a lock.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import config

logger = logging.getLogger("ai_investment.storage")

PORTFOLIO_PATH = config.DB_PATH / "portfolios.json"
CHAT_HISTORY_PATH = config.DB_PATH / "chat_history.json"
MAX_CHAT_MESSAGES_PER_SESSION = 100
MAX_STORED_SESSIONS = 50

_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _read_json(path: Path) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read %s: %s", path, exc)
    return {}


def _write_json(path: Path, data: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
    except Exception as exc:
        logger.error("Failed to write %s: %s", path, exc)


def save_portfolio(user_id: str, goals: list[dict[str, Any]]) -> dict[str, Any]:
    with _lock:
        store = _read_json(PORTFOLIO_PATH)
        if not isinstance(store, dict):
            store = {}
        store[user_id] = {"goals": goals, "updated_at": _now_iso()}
        _write_json(PORTFOLIO_PATH, store)
    return {"status": "saved", "goal_count": len(goals)}


def load_portfolio(user_id: str) -> dict[str, Any]:
    store = _read_json(PORTFOLIO_PATH)
    if isinstance(store, dict) and user_id in store:
        entry = store[user_id]
        return {"goals": entry.get("goals", []), "updated_at": entry.get("updated_at", "")}
    return {"goals": [], "updated_at": ""}


def save_chat_history(session_id: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    with _lock:
        store = _read_json(CHAT_HISTORY_PATH)
        if not isinstance(store, dict):
            store = {}
        trimmed = messages[-MAX_CHAT_MESSAGES_PER_SESSION:]
        store[session_id] = {"messages": trimmed, "updated_at": _now_iso()}
        if len(store) > MAX_STORED_SESSIONS:
            ordered = sorted(store.items(), key=lambda x: x[1].get("updated_at", ""), reverse=True)
            store = dict(ordered[:MAX_STORED_SESSIONS])
        _write_json(CHAT_HISTORY_PATH, store)
    return {"status": "saved", "message_count": len(trimmed)}


def load_chat_history(session_id: str) -> dict[str, Any]:
    store = _read_json(CHAT_HISTORY_PATH)
    if isinstance(store, dict) and session_id in store:
        entry = store[session_id]
        return {"messages": entry.get("messages", []), "updated_at": entry.get("updated_at", "")}
    return {"messages": [], "updated_at": ""}
