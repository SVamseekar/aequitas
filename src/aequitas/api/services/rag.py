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

    system = (
        "You are a UK bus transport policy analyst for the Aequitas platform. "
        "Answer based ONLY on the provided evidence. If the evidence doesn't "
        "cover the question, say so. Be concise and cite specific statistics."
    )
    context_line = f"User is viewing {dim} for region={region} ({urban_rural})."

    messages = [{"role": "user", "parts": [f"{system}\n\n{context_line}\n\nEvidence:\n{evidence}"]}]
    messages.append({"role": "model", "parts": ["Understood. I'll answer based on the provided evidence."]})

    # Add history (last 3 turns = 6 messages)
    if history:
        for msg in history[-6:]:
            # Support both HistoryMessage objects and raw dicts
            role_val = getattr(msg, "role", None) or msg.get("role", "")
            content_val = getattr(msg, "content", None) or msg.get("content", "")
            role = "user" if role_val == "user" else "model"
            messages.append({"role": role, "parts": [content_val]})

    messages.append({"role": "user", "parts": [query]})
    return messages


async def stream_gemini(
    messages: list[dict],
    api_key: str,
    conversation_id: str | None = None,
    source_sections: list[str] | None = None,
) -> AsyncGenerator[dict, None]:
    """Stream Gemini Flash response as SSE events."""
    conv_id = conversation_id or str(uuid.uuid4())

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        response = model.generate_content(
            messages,
            stream=True,
        )

        for chunk in response:
            if chunk.text:
                yield {"event": "chunk", "data": {"text": chunk.text}}

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
            "data": {"message": "An error occurred generating the response", "code": "gemini_error"},
        }
