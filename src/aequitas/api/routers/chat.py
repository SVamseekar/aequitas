"""Chat router — POST /api/chat (SSE streaming)."""
from __future__ import annotations

import json
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from aequitas.api.auth import verify_supabase_jwt
from aequitas.api.config import ApiConfig
from aequitas.api.deps import get_embedding_model, get_faiss
from aequitas.api.models.requests import ChatRequest
from aequitas.api.services.rag import build_prompt, retrieve_chunks, stream_gemini

router = APIRouter(tags=["chat"])

# Simple in-memory rate limiter: max 10 requests per 60s per user
_RATE_LIMIT = 10
_RATE_WINDOW = 60.0
_request_log: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(user_id: str) -> None:
    """Raise 429 if user exceeds rate limit."""
    now = time.monotonic()
    timestamps = _request_log[user_id]
    # Prune old entries
    _request_log[user_id] = [t for t in timestamps if now - t < _RATE_WINDOW]
    if len(_request_log[user_id]) >= _RATE_LIMIT:
        raise HTTPException(429, "Rate limit exceeded — max 10 requests per minute")
    _request_log[user_id].append(now)


@router.post("/chat")
async def chat(
    req: ChatRequest,
    user: dict = Depends(verify_supabase_jwt),
) -> EventSourceResponse:
    """Stream Gemini response grounded in FAISS-retrieved narratives."""
    _check_rate_limit(user.get("sub", "anon"))
    faiss_index, faiss_metadata = get_faiss()
    embedding_model = get_embedding_model()

    if faiss_index is None or embedding_model is None:
        raise HTTPException(503, "Chat is unavailable — FAISS index not loaded")

    cfg = ApiConfig()

    # Retrieve
    chunks = retrieve_chunks(
        req.query, embedding_model, faiss_index, faiss_metadata, context=req.context
    )
    source_sections = list({c["section_id"] for c in chunks})

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
