"""User-scoped profiles router (policy_interests)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aequitas.api.auth import db
from aequitas.api.auth.dependencies import require_session

router = APIRouter(tags=["profiles"])


class ProfileUpdate(BaseModel):
    policy_interests: list[str] = Field(default_factory=list)


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


@router.get("/profile")
async def get_profile(session: dict = Depends(require_session)) -> dict:
    pool = await db.get_pool()
    row = await db.get_profile(pool, user_id=session["user_id"])
    if row is None:
        row = await db.get_or_create_profile(pool, user_id=session["user_id"])
    return _serialize(row)


@router.patch("/profile")
async def update_profile(
    body: ProfileUpdate, session: dict = Depends(require_session)
) -> dict:
    pool = await db.get_pool()
    await db.get_or_create_profile(pool, user_id=session["user_id"])
    row = await db.update_profile_policy_interests(
        pool, user_id=session["user_id"], policy_interests=body.policy_interests
    )
    if row is None:
        raise HTTPException(404, "Profile not found")
    return _serialize(row)
