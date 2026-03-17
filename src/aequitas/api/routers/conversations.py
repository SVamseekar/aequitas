"""Conversations router — CRUD for persisted chat sessions via Supabase."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from aequitas.api.auth import verify_supabase_jwt

router = APIRouter(tags=["conversations"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ConversationCreate(BaseModel):
    title: str


class MessageCreate(BaseModel):
    role: str
    content: str


# ---------------------------------------------------------------------------
# Supabase client helper
# ---------------------------------------------------------------------------

def _get_supabase() -> Any:
    """Return Supabase admin client, or raise 503 if not configured."""
    try:
        import os
        from supabase import create_client  # type: ignore[import-untyped]

        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            raise RuntimeError("Supabase not configured")
        return create_client(url, key)
    except Exception as exc:
        raise HTTPException(503, f"Supabase unavailable: {exc}") from exc


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/conversations")
async def list_conversations(user: dict = Depends(verify_supabase_jwt)) -> list[dict]:
    """List authenticated user's conversations, newest first."""
    sb = _get_supabase()
    resp = (
        sb.table("conversations")
        .select("*")
        .eq("user_id", user["sub"])
        .order("updated_at", desc=True)
        .limit(50)
        .execute()
    )
    return resp.data or []


@router.post("/conversations", status_code=201)
async def create_conversation(
    body: ConversationCreate,
    user: dict = Depends(verify_supabase_jwt),
) -> dict:
    """Create a new conversation for the authenticated user."""
    sb = _get_supabase()
    resp = (
        sb.table("conversations")
        .insert({"user_id": user["sub"], "title": body.title})
        .execute()
    )
    if not resp.data:
        raise HTTPException(500, "Failed to create conversation")
    return resp.data[0]


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: UUID,
    user: dict = Depends(verify_supabase_jwt),
) -> list[dict]:
    """Return all messages for a conversation (ownership verified via RLS)."""
    sb = _get_supabase()
    resp = (
        sb.table("messages")
        .select("*")
        .eq("conversation_id", str(conversation_id))
        .eq("user_id", user["sub"])
        .order("created_at", desc=False)
        .execute()
    )
    return resp.data or []


@router.post("/conversations/{conversation_id}/messages", status_code=201)
async def add_message(
    conversation_id: UUID,
    body: MessageCreate,
    user: dict = Depends(verify_supabase_jwt),
) -> dict:
    """Add a message to a conversation."""
    if body.role not in ("user", "assistant"):
        raise HTTPException(400, "role must be 'user' or 'assistant'")
    sb = _get_supabase()
    resp = (
        sb.table("messages")
        .insert({
            "conversation_id": str(conversation_id),
            "user_id": user["sub"],
            "role": body.role,
            "content": body.content,
        })
        .execute()
    )
    if not resp.data:
        raise HTTPException(500, "Failed to save message")
    # Touch conversation updated_at
    sb.table("conversations").update({"updated_at": "now()"}).eq("id", str(conversation_id)).execute()
    return resp.data[0]


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    user: dict = Depends(verify_supabase_jwt),
) -> None:
    """Delete a conversation and its messages (cascades via DB)."""
    sb = _get_supabase()
    sb.table("conversations").delete().eq("id", str(conversation_id)).eq("user_id", user["sub"]).execute()
