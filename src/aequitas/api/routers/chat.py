"""Chat router — POST /api/chat (SSE streaming)."""
from __future__ import annotations

import json
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from aequitas.api.auth.dependencies import require_session
from aequitas.api.config import ApiConfig
from aequitas.api.deps import get_embedding_model, get_faiss
from aequitas.api.models.requests import ChatRequest
from aequitas.api.services.rag import build_prompt, retrieve_chunks, stream_gemini

router = APIRouter(tags=["chat"])

import sqlite3

# Persistent SQLite-backed rate limiter: max 10 requests per 60s per user
_RATE_LIMIT = 10
_RATE_WINDOW = 60.0


def _check_rate_limit(user_id: str) -> None:
    """Raise 429 if user exceeds rate limit using SQLite database-backed tracking."""
    cfg = ApiConfig()
    db_dir = cfg.db_path.parent
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "chat_rate_limit.sqlite"

    conn = sqlite3.connect(str(db_path), timeout=10.0)
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_rate_limits (
                    user_id TEXT,
                    timestamp REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_ts ON chat_rate_limits(user_id, timestamp)")

            now = time.time()
            cutoff = now - _RATE_WINDOW

            # Prune old entries
            conn.execute("DELETE FROM chat_rate_limits WHERE timestamp < ?", (cutoff,))

            # Count recent requests
            cursor = conn.execute(
                "SELECT COUNT(*) FROM chat_rate_limits WHERE user_id = ? AND timestamp >= ?",
                (user_id, cutoff)
            )
            count = cursor.fetchone()[0]

            if count >= _RATE_LIMIT:
                raise HTTPException(429, f"Rate limit exceeded — max {_RATE_LIMIT} requests per minute")

            # Record current request
            conn.execute(
                "INSERT INTO chat_rate_limits (user_id, timestamp) VALUES (?, ?)",
                (user_id, now)
            )
    finally:
        conn.close()


@router.post("/chat")
async def chat(
    req: ChatRequest,
    session: dict = Depends(require_session),
) -> EventSourceResponse:
    """Stream Gemini response grounded in FAISS-retrieved narratives.

    Request body uses ``query`` (not ``message`` / ``prompt``). Missing key or
    FAISS index returns HTTP 503 with a clear detail string before SSE starts.
    """
    _check_rate_limit(session.get("user_id", "anon"))
    faiss_index, faiss_metadata = get_faiss()
    embedding_model = get_embedding_model()

    if faiss_index is None or embedding_model is None:
        raise HTTPException(503, "Chat is unavailable — FAISS index not loaded")

    cfg = ApiConfig()
    if not (cfg.gemini_api_key and str(cfg.gemini_api_key).strip()):
        raise HTTPException(
            503,
            "Chat not configured — set GEMINI_API_KEY to enable the policy assistant",
        )

    # Retrieve
    chunks = retrieve_chunks(
        req.query, embedding_model, faiss_index, faiss_metadata, context=req.context
    )
    source_sections = list({c["section_id"] for c in chunks if "section_id" in c})

    # Build prompt
    messages = build_prompt(req.query, chunks, req.context, req.history)

    # Stream
    async def event_generator():
        async for event in stream_gemini(
            messages, cfg.gemini_api_key, req.conversation_id, source_sections
        ):
            yield {
                "event": event["event"],
                "data": json.dumps(event["data"]),
            }

    return EventSourceResponse(event_generator())
