"""Conversations router — tenant-scoped CRUD via asyncpg."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from aequitas.api.auth import db
from aequitas.api.auth.dependencies import require_session

router = APIRouter(tags=["conversations"])


class ConversationCreate(BaseModel):
    title: str


class MessageCreate(BaseModel):
    role: str
    content: str


def _serialize_row(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = str(v) if hasattr(v, "hex") else v
    return out


@router.get("/conversations")
async def list_conversations(session: dict = Depends(require_session)) -> list[dict]:
    """List active tenant's conversations, newest first."""
    pool = await db.get_pool()
    rows = await db.list_conversations(pool, tenant_id=session["tenant_id"])
    return [_serialize_row(r) for r in rows]


@router.post("/conversations", status_code=201)
async def create_conversation(
    body: ConversationCreate,
    session: dict = Depends(require_session),
) -> dict:
    """Create a new conversation for the active tenant."""
    pool = await db.get_pool()
    row = await db.create_conversation(
        pool,
        tenant_id=session["tenant_id"],
        user_id=session["user_id"],
        title=body.title,
    )
    return _serialize_row(row)


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: UUID,
    session: dict = Depends(require_session),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[dict]:
    """Return messages for a conversation with pagination."""
    pool = await db.get_pool()
    conv = await db.get_conversation(
        pool, tenant_id=session["tenant_id"], conversation_id=str(conversation_id)
    )
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    rows = await db.list_messages(
        pool,
        tenant_id=session["tenant_id"],
        conversation_id=str(conversation_id),
        offset=offset,
        limit=limit,
    )
    return [_serialize_row(r) for r in rows]


@router.post("/conversations/{conversation_id}/messages", status_code=201)
async def add_message(
    conversation_id: UUID,
    body: MessageCreate,
    session: dict = Depends(require_session),
) -> dict:
    """Add a message to a conversation."""
    if body.role not in ("user", "assistant"):
        raise HTTPException(400, "role must be 'user' or 'assistant'")
    pool = await db.get_pool()
    conv = await db.get_conversation(
        pool, tenant_id=session["tenant_id"], conversation_id=str(conversation_id)
    )
    if conv is None:
        raise HTTPException(404, "Conversation not found")

    row = await db.create_message(
        pool,
        tenant_id=session["tenant_id"],
        conversation_id=str(conversation_id),
        user_id=session["user_id"],
        role=body.role,
        content=body.content,
    )
    await db.touch_conversation(
        pool, tenant_id=session["tenant_id"], conversation_id=str(conversation_id)
    )
    return _serialize_row(row)


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: UUID,
    body: ConversationCreate,
    session: dict = Depends(require_session),
) -> dict:
    """Update conversation title."""
    pool = await db.get_pool()
    row = await db.update_conversation_title(
        pool,
        tenant_id=session["tenant_id"],
        conversation_id=str(conversation_id),
        title=body.title,
    )
    if row is None:
        raise HTTPException(404, "Conversation not found")
    return _serialize_row(row)


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    session: dict = Depends(require_session),
) -> None:
    """Delete a conversation and its messages (cascades via DB)."""
    pool = await db.get_pool()
    conv = await db.get_conversation(
        pool, tenant_id=session["tenant_id"], conversation_id=str(conversation_id)
    )
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    await db.delete_conversation(
        pool, tenant_id=session["tenant_id"], conversation_id=str(conversation_id)
    )
