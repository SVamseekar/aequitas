"""RAG service — FAISS retrieval + Gemini streaming."""
from __future__ import annotations

import uuid
from typing import Any, AsyncGenerator

import numpy as np
from loguru import logger


def retrieve_chunks(
    query: str,
    embedding_model: Any,
    faiss_index: Any,
    faiss_metadata: list[dict],
    top_k: int = 5,
    context: dict | None = None,
) -> list[dict]:
    """Embed query and retrieve top-k nearest narrative chunks."""
    query_vec = embedding_model.encode([query], normalize_embeddings=True)
    query_np = np.array(query_vec, dtype=np.float32)

    scores, indices = faiss_index.search(query_np, top_k)

    results = []
    for i, idx in enumerate(indices[0]):
        if idx < 0 or idx >= len(faiss_metadata):
            continue
        chunk = faiss_metadata[idx].copy()
        chunk["score"] = float(scores[0][i])
        results.append(chunk)
    return results


def build_prompt(
    query: str,
    chunks: list[dict],
    context: dict | None = None,
    history: list[dict] | None = None,
) -> list[dict]:
    """Build Gemini message list from query + retrieved chunks."""
    evidence = "\n\n---\n\n".join(c["text"] for c in chunks)
    dim = context.get("dimension", "unknown") if context else "unknown"
    region = context.get("region", "all") if context else "all"
    urban_rural = context.get("urban_rural", "all") if context else "all"

    country = (context or {}).get("country") or "england"
    if str(country).lower() == "ireland":
        system = (
            "You are an NTA / Republic of Ireland bus briefing analyst for Aequitas. "
            "Answer ONLY from the Irish evidence (TFI, CSO Small Areas, Pobal HP 2022). "
            "Do not mention England statutes, BODS, IMD, LSOA, TAG, or BSA. "
            "If the evidence does not cover the question, say so."
        )
    elif str(country).lower() == "netherlands":
        system = (
            "You are a Netherlands OV briefing analyst for Aequitas. "
            "Answer ONLY from Dutch evidence (OVapi, CBS buurten, SES-WOA). "
            "Do not mention England or Ireland statutes, BODS, IMD, LSOA, TFI, or BSA. "
            "If the Netherlands index is missing, say the Netherlands index is not built."
        )
    else:
        system = (
            "You are a UK bus transport policy analyst for the Aequitas platform. "
            "Answer based ONLY on the provided evidence. If the evidence doesn't "
            "cover the question, say so. Be concise and cite specific statistics."
        )
    context_line = f"User is viewing {dim} for region={region} ({urban_rural})."

    messages = [{"role": "user", "parts": [f"{system}\n\n{context_line}\n\nEvidence:\n{evidence}"]}]
    messages.append({"role": "model", "parts": ["Understood. I'll answer based on the provided evidence."]})

    if history:
        for msg in history[-6:]:
            role_val = getattr(msg, "role", None) or msg.get("role", "")
            content_val = getattr(msg, "content", None) or msg.get("content", "")
            role = "user" if role_val == "user" else "model"
            messages.append({"role": role, "parts": [content_val]})

    messages.append({"role": "user", "parts": [query]})
    return messages


def _messages_to_contents(messages: list[dict]) -> list[dict]:
    """Convert legacy parts-shaped messages to google.genai Content dicts."""
    contents: list[dict] = []
    for msg in messages:
        role = msg.get("role", "user")
        # google.genai uses "model" for assistant turns as well.
        parts = msg.get("parts") or []
        text = " ".join(str(p) for p in parts) if isinstance(parts, list) else str(parts)
        contents.append({"role": role, "parts": [{"text": text}]})
    return contents


async def stream_gemini(
    messages: list[dict],
    api_key: str,
    conversation_id: str | None = None,
    source_sections: list[str] | None = None,
) -> AsyncGenerator[dict, None]:
    """Stream Gemini Flash response as SSE events.

    Prefers the ``google.genai`` SDK when installed; falls back to the older
    ``google.generativeai`` package. Empty/missing API keys must be rejected
    by the router before calling this (503).
    """
    conv_id = conversation_id or str(uuid.uuid4())

    if not api_key or not str(api_key).strip():
        yield {
            "event": "error",
            "data": {
                "message": "Chat not configured — set GEMINI_API_KEY",
                "code": "not_configured",
            },
        }
        return

    try:
        async for event in _stream_with_new_sdk(messages, api_key):
            yield event
        yield {
            "event": "done",
            "data": {
                "conversation_id": conv_id,
                "sources": source_sections or [],
            },
        }
        return
    except ImportError:
        logger.debug("google.genai not installed — falling back to google.generativeai")
    except Exception as e:
        logger.warning(f"google.genai path failed ({type(e).__name__}: {e}); trying legacy SDK")

    try:
        async for event in _stream_with_legacy_sdk(messages, api_key):
            yield event
        yield {
            "event": "done",
            "data": {
                "conversation_id": conv_id,
                "sources": source_sections or [],
            },
        }
    except Exception as e:
        logger.error(f"Gemini streaming error: {type(e).__name__}: {e}")
        yield {
            "event": "error",
            "data": {
                "message": f"Chat model error: {type(e).__name__}. Check GEMINI_API_KEY and model access.",
                "code": "gemini_error",
            },
        }


async def _stream_with_new_sdk(messages: list[dict], api_key: str) -> AsyncGenerator[dict, None]:
    """Stream via google.genai (preferred, non-deprecated)."""
    from google import genai  # type: ignore[import-untyped]

    client = genai.Client(api_key=api_key)
    contents = _messages_to_contents(messages)

    # stream is sync iterator in many SDK versions — wrap yields.
    stream = client.models.generate_content_stream(
        model="gemini-2.0-flash",
        contents=contents,
    )
    for chunk in stream:
        text = getattr(chunk, "text", None)
        if text:
            yield {"event": "chunk", "data": {"text": text}}


async def _stream_with_legacy_sdk(messages: list[dict], api_key: str) -> AsyncGenerator[dict, None]:
    """Stream via google.generativeai (deprecated but still installed)."""
    import google.generativeai as genai  # type: ignore[import-untyped]

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(messages, stream=True)
    for chunk in response:
        if getattr(chunk, "text", None):
            yield {"event": "chunk", "data": {"text": chunk.text}}
