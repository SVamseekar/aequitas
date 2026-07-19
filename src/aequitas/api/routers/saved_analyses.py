"""Tenant-scoped saved analyses router."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aequitas.api.auth import db
from aequitas.api.auth.dependencies import require_session

router = APIRouter(tags=["saved_analyses"])


class SavedAnalysisCreate(BaseModel):
    title: str
    content: str
    section_id: str | None = None
    dimension: str | None = None
    tags: list[str] = Field(default_factory=list)


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


@router.get("/saved-analyses")
async def list_analyses(session: dict = Depends(require_session)) -> list[dict]:
    pool = await db.get_pool()
    rows = await db.list_saved_analyses(pool, tenant_id=session["tenant_id"])
    return [_serialize(r) for r in rows]


@router.post("/saved-analyses", status_code=201)
async def create_analysis(
    body: SavedAnalysisCreate, session: dict = Depends(require_session)
) -> dict:
    pool = await db.get_pool()
    row = await db.create_saved_analysis(
        pool,
        tenant_id=session["tenant_id"],
        user_id=session["user_id"],
        title=body.title,
        content=body.content,
        section_id=body.section_id,
        dimension=body.dimension,
        tags=body.tags,
    )
    return _serialize(row)


@router.delete("/saved-analyses/{analysis_id}", status_code=204)
async def delete_analysis(
    analysis_id: UUID, session: dict = Depends(require_session)
) -> None:
    pool = await db.get_pool()
    await db.delete_saved_analysis(
        pool, tenant_id=session["tenant_id"], analysis_id=str(analysis_id)
    )
