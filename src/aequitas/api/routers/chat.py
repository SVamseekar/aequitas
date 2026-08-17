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
    country = str((req.context or {}).get("country") or "england").lower()
    faiss_index, faiss_metadata = get_faiss(country)
    embedding_model = get_embedding_model()

    if faiss_index is None or embedding_model is None or not faiss_metadata:
        if country == "ireland":
            raise HTTPException(503, "Ireland chat index is not built")
        if country == "netherlands":
            raise HTTPException(503, "Netherlands index not built.")
        if country == "france":
            raise HTTPException(503, "France index not built.")
        raise HTTPException(503, "Chat is unavailable — FAISS index not loaded")

    cfg = ApiConfig()

    # Retrieve (works without Gemini)
    chunks = retrieve_chunks(
        req.query, embedding_model, faiss_index, faiss_metadata, context=req.context
    )
    if country == "france":
        chunks = [c for c in chunks if not _mentions_foreign_statute(c.get("text") or "")]
    source_sections = list({c["section_id"] for c in chunks if "section_id" in c})

    has_gemini = bool(cfg.gemini_api_key and str(cfg.gemini_api_key).strip())
    messages = build_prompt(req.query, chunks, req.context, req.history)

    async def event_generator():
        if not has_gemini:
            text = _honest_retrieval_reply(country, chunks, req.query)
            yield {"event": "chunk", "data": json.dumps({"text": text})}
            yield {
                "event": "done",
                "data": json.dumps(
                    {
                        "conversation_id": req.conversation_id or "retrieve-only",
                        "sources": source_sections,
                        "generation": "retrieval_only",
                    }
                ),
            }
            return
        gemini_failed = False
        async for event in stream_gemini(
            messages, cfg.gemini_api_key, req.conversation_id, source_sections
        ):
            if event.get("event") == "error":
                gemini_failed = True
                text = _honest_retrieval_reply(country, chunks, req.query)
                extra = " Generation failed; showing retrieved chunks instead of another country’s warehouse."
                yield {"event": "chunk", "data": json.dumps({"text": text + extra})}
                yield {
                    "event": "done",
                    "data": json.dumps(
                        {
                            "conversation_id": req.conversation_id or "retrieve-only",
                            "sources": source_sections,
                            "generation": "retrieval_only",
                        }
                    ),
                }
                return
            yield {
                "event": event["event"],
                "data": json.dumps(event["data"]),
            }
        if gemini_failed:
            return

    return EventSourceResponse(event_generator())


_FOREIGN_STATUTE = (
    "bsa 2025",
    "bus services act",
    "imd decile",
    "imd 2025",
    "pobal hp",
    "pobal",
)


def _mentions_foreign_statute(text: str) -> bool:
    blob = text.lower()
    return any(tok in blob for tok in _FOREIGN_STATUTE)


def _honest_retrieval_reply(country: str, chunks: list[dict], query: str = "") -> str:
    place = {
        "ireland": "Republic of Ireland",
        "netherlands": "Netherlands",
        "france": "France",
    }.get(country, "England")
    if country == "france" and _mentions_foreign_statute(query):
        return (
            "Those statutes (BSA 2025 / IMD / Pobal HP) are not the France pack. "
            "This index only holds NAP × F-EDI × IRIS narratives."
        )
    if not chunks:
        return (
            f"Retrieval ran on the {place} index and found no matching briefing chunks. "
            "Generation is off until GEMINI_API_KEY is set — I will not answer from another country."
        )
    parts = [
        f"Retrieved {len(chunks)} {place} briefing chunk(s). "
        "This is retrieval only — no generated answer from another country’s warehouse.",
        "",
    ]
    for i, c in enumerate(chunks, 1):
        sid = c.get("section_id") or "section"
        region = c.get("region") or "all"
        text = (c.get("text") or "").strip()
        parts.append(f"{i}. [{sid} · {region}]\n{text}")
    return "\n\n".join(parts)
