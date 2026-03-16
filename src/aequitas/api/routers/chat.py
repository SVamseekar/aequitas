"""Chat router — POST /api/chat (SSE streaming)."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from aequitas.api.config import ApiConfig
from aequitas.api.deps import get_embedding_model, get_faiss
from aequitas.api.models.requests import ChatRequest
from aequitas.api.services.rag import build_prompt, retrieve_chunks, stream_gemini

router = APIRouter()


@router.post("/chat")
async def chat(req: ChatRequest) -> EventSourceResponse:
    """Stream Gemini response grounded in FAISS-retrieved narratives."""
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
