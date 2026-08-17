"""Dependency injection — shared resources loaded at startup."""
from __future__ import annotations

import json
from collections.abc import Generator
from contextlib import asynccontextmanager
from typing import Any

import duckdb
from loguru import logger

from fastapi import HTTPException, Query

from aequitas.api.config import ApiConfig

_state: dict[str, Any] = {}


def _open_readonly(path) -> duckdb.DuckDBPyConnection | None:
    if path is None:
        return None
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return None
    return duckdb.connect(str(p), read_only=True)


def get_db() -> Generator[duckdb.DuckDBPyConnection | None, None, None]:
    """England warehouse (default). Prefer get_country_db when country is known."""
    conn = _open_readonly(_state.get("db_path"))
    try:
        yield conn
    finally:
        if conn is not None:
            conn.close()


def _live_path(country: str):
    key = (country or "england").strip().lower()
    if key == "ireland":
        return _state.get("ie_db_path")
    if key == "netherlands":
        return _state.get("nl_db_path")
    if key == "france":
        return _state.get("fr_db_path")
    return _state.get("db_path")


def get_country_db(
    country: str = "england",
    pack: str | None = None,
) -> Generator[duckdb.DuckDBPyConnection | None, None, None]:
    """Open the warehouse for `country` (+ optional dated pack). Ireland never falls back to England.

    Routers declare `country: str = Query("england")` and pass it, or use
    `Depends(country_warehouse)`.
    """
    key = (country or "england").strip().lower()
    live = _live_path(key)
    requested = (pack or "").strip()
    if requested and requested.lower() not in {"current", "latest"}:
        from aequitas.warehouse.packs import warehouse_for_pack

        path = warehouse_for_pack(key, requested, live)
        if path is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown pack {requested!r} for {key}. Not falling back to another country.",
            )
        conn = _open_readonly(path)
        try:
            yield conn
        finally:
            if conn is not None:
                conn.close()
        return
    conn = _open_readonly(live)
    try:
        yield conn
    finally:
        if conn is not None:
            conn.close()


def country_warehouse(
    country: str = Query("england"),
    pack: str | None = Query(None),
    as_of: str | None = Query(None),
) -> Generator[duckdb.DuckDBPyConnection | None, None, None]:
    """FastAPI dependency: bind `country` + optional pack/as_of to the right DuckDB."""
    yield from get_country_db(country, pack=pack or as_of)


def resolve_country_db(country: str, pack: str | None = None) -> duckdb.DuckDBPyConnection | None:
    key = (country or "england").strip().lower()
    live = _live_path(key)
    if pack and pack.lower() not in {"current", "latest"}:
        from aequitas.warehouse.packs import warehouse_for_pack

        path = warehouse_for_pack(key, pack, live)
        if path is None:
            return None
        return _open_readonly(path)
    return _open_readonly(live)


def get_faiss(country: str = "england") -> tuple[Any, list[dict] | None]:
    """Return (faiss_index, faiss_metadata) for that country, or (None, None)."""
    by_c = _state.get("faiss_by_country") or {}
    key = (country or "england").lower()
    if key in by_c:
        return by_c[key]
    if key == "england":
        return _state.get("faiss_index"), _state.get("faiss_metadata")
    return None, None


def get_embedding_model() -> Any:
    """Return the sentence-transformer embedding model or None."""
    return _state.get("embedding_model")


@asynccontextmanager
async def lifespan(app: Any):  # type: ignore[type-arg]
    """Load DuckDB + FAISS on startup, close on shutdown."""
    import os

    cfg = ApiConfig()

    # Ensure DATABASE_URL is visible to auth.db.get_pool()
    if "DATABASE_URL" not in os.environ and cfg.database_url:
        os.environ["DATABASE_URL"] = cfg.database_url

    # Postgres tenancy schema (idempotent)
    try:
        from aequitas.api.auth import db as auth_db

        pool = await auth_db.get_pool()
        await auth_db.run_migrations(pool)
        logger.info("Postgres tenancy schema ready")
    except Exception as exc:
        logger.warning(f"Postgres tenancy schema not applied: {exc}")

    # DuckDB — store path only; each request opens a fresh read-only connection
    if cfg.db_path.exists():
        logger.info(f"DuckDB warehouse found: {cfg.db_path}")
        _state["db_path"] = cfg.db_path
    else:
        logger.warning(
            f"Warehouse not found at {cfg.db_path} — run pipeline first. "
            "API will start but return empty results."
        )

    ie_path = cfg.ireland_db_path
    if ie_path.exists():
        logger.info(f"Ireland warehouse found: {ie_path}")
        _state["ie_db_path"] = ie_path
    else:
        logger.info(f"Ireland warehouse not found at {ie_path} — /api/*?country=ireland stays empty.")

    nl_path = cfg.netherlands_db_path
    if nl_path.exists():
        logger.info(f"Netherlands warehouse found: {nl_path}")
        _state["nl_db_path"] = nl_path
    else:
        logger.info(f"Netherlands warehouse not found at {nl_path} — /api/*?country=netherlands stays empty.")

    fr_path = cfg.france_db_path
    if fr_path.exists():
        logger.info(f"France warehouse found: {fr_path}")
        _state["fr_db_path"] = fr_path
    else:
        logger.info(f"France warehouse not found at {fr_path} — /api/*?country=france stays empty.")

    if not os.environ.get("PYTEST_CURRENT_TEST"):
        try:
            from aequitas.warehouse.packs import ensure_current_registered

            if cfg.db_path.exists():
                ensure_current_registered("england", cfg.db_path, pack_id="2026-08-01")
            if ie_path.exists():
                ensure_current_registered("ireland", ie_path, pack_id="2026-08-13")
            if nl_path.exists():
                ensure_current_registered("netherlands", nl_path)
            if fr_path.exists():
                ensure_current_registered("france", fr_path)
        except Exception as exc:
            logger.warning("Pack registry: {}", exc)

    # Gemini API key check
    if not cfg.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set — chat responses will fail")

    # FAISS (optional — chat won't work without it but dashboard still does)
    import faiss

    by_country: dict[str, tuple[Any, list]] = {}
    if cfg.faiss_index_path.exists():
        logger.info(f"Loading FAISS index: {cfg.faiss_index_path}")
        _state["faiss_index"] = faiss.read_index(str(cfg.faiss_index_path))
        _state["faiss_metadata"] = json.loads(cfg.faiss_metadata_path.read_text())
        by_country["england"] = (_state["faiss_index"], _state["faiss_metadata"])
    else:
        logger.warning(f"FAISS index not found at {cfg.faiss_index_path} — England chat disabled")

    if cfg.ireland_faiss_index_path.exists() and cfg.ireland_faiss_metadata_path.exists():
        logger.info(f"Loading Ireland FAISS index: {cfg.ireland_faiss_index_path}")
        ie_idx = faiss.read_index(str(cfg.ireland_faiss_index_path))
        ie_meta = json.loads(cfg.ireland_faiss_metadata_path.read_text())
        by_country["ireland"] = (ie_idx, ie_meta)
    else:
        logger.warning(
            f"Ireland FAISS not found at {cfg.ireland_faiss_index_path} — Ireland chat retrieval disabled"
        )

    if cfg.france_faiss_index_path.exists() and cfg.france_faiss_metadata_path.exists():
        logger.info(f"Loading France FAISS index: {cfg.france_faiss_index_path}")
        fr_idx = faiss.read_index(str(cfg.france_faiss_index_path))
        fr_meta = json.loads(cfg.france_faiss_metadata_path.read_text())
        by_country["france"] = (fr_idx, fr_meta)
    else:
        logger.warning(
            f"France FAISS not found at {cfg.france_faiss_index_path} — France chat retrieval disabled"
        )

    _state["faiss_by_country"] = by_country
    if by_country:
        from sentence_transformers import SentenceTransformer

        _state["embedding_model"] = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("FAISS + embedding model loaded for {}", list(by_country))
    else:
        logger.warning("No country FAISS index — chat disabled")

    yield

    _state.clear()
