"""Tenant-scoped policy notes router."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from aequitas.api.auth import db
from aequitas.api.auth.dependencies import require_session

router = APIRouter(tags=["policy_notes"])


class PolicyNoteCreate(BaseModel):
    dimension: str
    region: str = "all"
    stance: str | None = None
    thesis: str
    critique: str | None = None


class PolicyNoteUpdate(BaseModel):
    dimension: str | None = None
    region: str | None = None
    stance: str | None = None
    thesis: str | None = None
    critique: str | None = None


def _serialize(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif hasattr(v, "hex"):
            out[k] = str(v)
        else:
            out[k] = v
    return out


@router.get("/policy-notes")
async def list_notes(session: dict = Depends(require_session)) -> list[dict]:
    pool = await db.get_pool()
    rows = await db.list_policy_notes(pool, tenant_id=session["tenant_id"])
    return [_serialize(r) for r in rows]


@router.post("/policy-notes", status_code=201)
async def create_note(
    body: PolicyNoteCreate, session: dict = Depends(require_session)
) -> dict:
    if body.stance is not None and body.stance not in (
        "priority",
        "monitor",
        "adequate",
    ):
        raise HTTPException(400, "stance must be priority, monitor, or adequate")
    pool = await db.get_pool()
    row = await db.create_policy_note(
        pool,
        tenant_id=session["tenant_id"],
        user_id=session["user_id"],
        dimension=body.dimension,
        region=body.region,
        stance=body.stance,
        thesis=body.thesis,
        critique=body.critique,
    )
    return _serialize(row)


@router.patch("/policy-notes/{note_id}")
async def update_note(
    note_id: UUID,
    body: PolicyNoteUpdate,
    session: dict = Depends(require_session),
) -> dict:
    pool = await db.get_pool()
    row = await db.update_policy_note(
        pool,
        tenant_id=session["tenant_id"],
        note_id=str(note_id),
        dimension=body.dimension,
        region=body.region,
        stance=body.stance,
        thesis=body.thesis,
        critique=body.critique,
    )
    if row is None:
        raise HTTPException(404, "Policy note not found")
    return _serialize(row)


@router.delete("/policy-notes/{note_id}", status_code=204)
async def delete_note(
    note_id: UUID, session: dict = Depends(require_session)
) -> None:
    pool = await db.get_pool()
    await db.delete_policy_note(
        pool, tenant_id=session["tenant_id"], note_id=str(note_id)
    )
