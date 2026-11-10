"""LLM providers — one small interface, two backends.

Primary: Inception Labs (Mercury, OpenAI-compatible API) — the live provider.
Fallback: Google Gemini. Every call tries the primary first, then the other
provider when it is configured. If neither is configured, callers get a
clear RuntimeError and must use their rule-based fallback — the app never
crashes for lack of an LLM key.
"""
from __future__ import annotations

import json
import logging
import time

import requests

import config

logger = logging.getLogger("ai_investment.llm")

# Inception caps output per model; Mercury 2.5 allows 65k, keep requests sane.
DEFAULT_MAX_TOKENS = 1024


class LLMError(RuntimeError):
    pass


def _openai_chat(base_url: str, api_key: str, model: str,
                 messages: list[dict], temperature: float,
                 max_tokens: int) -> str:
    """One OpenAI-compatible /chat/completions call. No SDK needed."""
    resp = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        json={"model": model, "messages": messages,
              "temperature": temperature, "max_tokens": max_tokens},
        timeout=60,
    )
    if resp.status_code != 200:
        raise LLMError(f"LLM API {resp.status_code}: {resp.text[:300]}")
    try:
        return resp.json()["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, ValueError) as exc:
        raise LLMError(f"Unexpected LLM response shape: {exc}") from exc


def _call_inception(messages: list[dict], temperature: float,
                    max_tokens: int) -> str:
    if not config.INCEPTION_API_KEY:
        raise LLMError("INCEPTION_API_KEY is not configured")
    return _openai_chat(config.INCEPTION_BASE_URL, config.INCEPTION_API_KEY,
                        config.INCEPTION_MODEL, messages, temperature,
                        max_tokens)


def _call_gemini(messages: list[dict], temperature: float,
                 max_tokens: int) -> str:
    if not config.GOOGLE_API_KEY:
        raise LLMError("GOOGLE_API_KEY is not configured")
    try:
        from google import genai
    except ImportError as exc:
        raise LLMError("google-genai is not installed") from exc

    client = genai.Client(api_key=config.GOOGLE_API_KEY)
    system_text = ""
    contents = []
    for msg in messages:
        if msg["role"] == "system":
            system_text = msg["content"]
        elif msg["role"] == "user":
            contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
        elif msg["role"] == "assistant":
            contents.append({"role": "model", "parts": [{"text": msg["content"]}]})
    cfg: dict = {"temperature": temperature, "max_output_tokens": max_tokens}
    if system_text:
        cfg["system_instruction"] = system_text
    response = client.models.generate_content(
        model=config.GEMINI_MODEL, contents=contents, config=cfg)
    return response.text or ""


_CALLERS = {"inception": _call_inception, "gemini": _call_gemini}


def available_providers() -> list[str]:
    """Provider names that have a key configured, primary first."""
    names = []
    if config.INCEPTION_API_KEY:
        names.append("inception")
    if config.GOOGLE_API_KEY:
        names.append("gemini")
    primary = config.LLM_PROVIDER if config.LLM_PROVIDER in names else None
    ordered = ([primary] if primary else []) + [n for n in names if n != primary]
    return ordered


def chat(messages: list[dict], temperature: float = 0.7,
         max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    """Chat completion with primary → fallback. Raises LLMError if none work."""
    providers = available_providers()
    if not providers:
        raise LLMError(
            "No LLM configured. Set INCEPTION_API_KEY (Inception Labs) or "
            "GOOGLE_API_KEY (Gemini) in .env"
        )
    errors = []
    for name in providers:
        try:
            return _CALLERS[name](messages, temperature, max_tokens)
        except Exception as exc:  # noqa: BLE001 — fall through to next provider
            logger.warning("%s failed, trying next provider: %s", name, exc)
            errors.append(f"{name}: {exc}")
    raise LLMError("All LLM providers failed: " + " | ".join(errors))


def generate(prompt: str, temperature: float = 0.3,
             max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    """Single-shot generation (JSON tasks, summaries)."""
    return chat([{"role": "user", "content": prompt}], temperature, max_tokens)


def parse_json_object(text: str) -> dict | None:
    """Best-effort JSON object extraction from LLM output (fences tolerated)."""
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except ValueError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(cleaned[start:end + 1])
                return parsed if isinstance(parsed, dict) else None
            except ValueError:
                return None
        return None


def parse_json_array(text: str) -> list | None:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, list) else None
    except ValueError:
        start, end = cleaned.find("["), cleaned.rfind("]")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(cleaned[start:end + 1])
                return parsed if isinstance(parsed, list) else None
            except ValueError:
                return None
        return None


def call_with_quota_retry(fn, operation: str, max_attempts: int = 4):
    """Retry quota (429) failures with backoff; other errors raise at once."""
    backoff = 1.5
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:
            msg = str(exc)
            if "429" not in msg and "RESOURCE_EXHAUSTED" not in msg:
                raise LLMError(f"{operation} failed: {exc}") from exc
            if attempt == max_attempts:
                raise LLMError(f"{operation} failed due to API quota: {exc}") from exc
            time.sleep(min(backoff, 45.0))
            backoff *= 2
