"""Dependency injection — shared resources loaded at startup."""
from __future__ import annotations

import json
from collections.abc import Generator
from contextlib import asynccontextmanager
from typing import Any

import duckdb
from loguru import logger

from aequitas.api.config import ApiConfig

_state: dict[str, Any] = {}


def get_db() -> Generator[duckdb.DuckDBPyConnection | None, None, None]:
    """FastAPI dependency — opens a fresh read-only DuckDB connection per request.

    The connection is automatically closed after the request completes.
    Yields None if warehouse path was not found at startup.
    """
    db_path = _state.get("db_path")
    if db_path is None:
        yield None
        return
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        yield conn
    finally:
        conn.close()


def get_faiss() -> tuple[Any, list[dict] | None]:
    """Return (faiss_index, faiss_metadata) or (None, None)."""
    return _state.get("faiss_index"), _state.get("faiss_metadata")


def get_embedding_model() -> Any:
    """Return the sentence-transformer embedding model or None."""
    return _state.get("embedding_model")


@asynccontextmanager
async def lifespan(app: Any):  # type: ignore[type-arg]
    """Load DuckDB + FAISS on startup, close on shutdown."""
    cfg = ApiConfig()

    # DuckDB — store path only; each request opens a fresh read-only connection
    if cfg.db_path.exists():
        logger.info(f"DuckDB warehouse found: {cfg.db_path}")
        _state["db_path"] = cfg.db_path
    else:
        logger.warning(f"Warehouse not found at {cfg.db_path} — run pipeline first. API will start but return empty results.")

    # Gemini API key check
    if not cfg.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set — chat responses will fail")

    # FAISS (optional — chat won't work without it but dashboard still does)
    if cfg.faiss_index_path.exists():
        import faiss
        logger.info(f"Loading FAISS index: {cfg.faiss_index_path}")
        _state["faiss_index"] = faiss.read_index(str(cfg.faiss_index_path))
        _state["faiss_metadata"] = json.loads(cfg.faiss_metadata_path.read_text())

        from sentence_transformers import SentenceTransformer
        _state["embedding_model"] = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("FAISS + embedding model loaded")
    else:
        logger.warning(f"FAISS index not found at {cfg.faiss_index_path} — chat disabled")

    yield

    _state.clear()
