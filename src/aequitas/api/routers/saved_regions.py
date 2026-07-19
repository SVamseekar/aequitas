"""Tenant-scoped saved regions router."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from aequitas.api.auth import db
from aequitas.api.auth.dependencies import require_session

router = APIRouter(tags=["saved_regions"])


class SavedRegionCreate(BaseModel):
    region_code: str
    region_name: str
    notes: str | None = None


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


@router.get("/saved-regions")
async def list_regions(session: dict = Depends(require_session)) -> list[dict]:
    pool = await db.get_pool()
    rows = await db.list_saved_regions(pool, tenant_id=session["tenant_id"])
    return [_serialize(r) for r in rows]


@router.post("/saved-regions", status_code=201)
async def create_region(
    body: SavedRegionCreate, session: dict = Depends(require_session)
) -> dict:
    pool = await db.get_pool()
    row = await db.create_saved_region(
        pool,
        tenant_id=session["tenant_id"],
        user_id=session["user_id"],
        region_code=body.region_code,
        region_name=body.region_name,
        notes=body.notes,
    )
    return _serialize(row)


@router.delete("/saved-regions/{region_id}", status_code=204)
async def delete_region(
    region_id: UUID, session: dict = Depends(require_session)
) -> None:
    pool = await db.get_pool()
    await db.delete_saved_region(
        pool, tenant_id=session["tenant_id"], region_id=str(region_id)
    )
