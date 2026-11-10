"""Local embeddings + vector store.

Sentence Transformers (all-MiniLM-L6-v2, 384-dim, CPU) and ChromaDB.
Both load lazily — importing this module never downloads a model or opens
a database, so the API boots and serves even on a box without torch.
"""
from __future__ import annotations

import hashlib
import threading
from functools import lru_cache
from typing import Any

import config

_model_lock = threading.Lock()
_model = None


def get_embedding_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer
                print(f"[embeddings] Loading {config.EMBEDDING_MODEL} "
                      f"on {config.EMBEDDING_DEVICE}")
                _model = SentenceTransformer(
                    config.EMBEDDING_MODEL, device=config.EMBEDDING_DEVICE)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = get_embedding_model()
    vectors = model.encode(
        texts, batch_size=config.EMBEDDING_BATCH_SIZE,
        show_progress_bar=len(texts) > 10,
        normalize_embeddings=True, convert_to_numpy=True,
    )
    return vectors.tolist()


def embed_query(query: str) -> list[float]:
    return embed_texts([query])[0]


def build_document_id(source: str, title: str, date: str, url: str = "") -> str:
    """Deterministic ID so re-ingestion is a no-op."""
    unique = f"{source}|{url}|{title}|{date}" if source != "csv" \
        else f"csv|{title}|{date}"
    digest = hashlib.sha256(unique.encode("utf-8", errors="ignore")).hexdigest()
    return f"news_{digest[:32]}"


def build_document_text(title: str, description: str,
                        ticker_tags: list[str] | None = None) -> str:
    parts = [f"Title: {title}", f"Description: {description}"]
    if ticker_tags:
        parts.append(f"TickerTags: {', '.join(ticker_tags)}")
    return "\n".join(parts)


@lru_cache(maxsize=1)
def get_chroma_collection():
    import chromadb
    client = chromadb.PersistentClient(path=str(config.DB_PATH))
    return client.get_or_create_collection(name=config.CHROMA_COLLECTION_NAME)


def get_collection_stats() -> dict[str, Any]:
    collection = get_chroma_collection()
    return {
        "collection_name": config.CHROMA_COLLECTION_NAME,
        "document_count": collection.count(),
        "embedding_model": config.EMBEDDING_MODEL,
        "db_path": str(config.DB_PATH),
    }
