"""Google OAuth login/callback/logout and session-tenant-switch routes."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from aequitas.api.auth import db
from aequitas.api.auth.dependencies import require_session
from aequitas.api.auth.oauth import get_google_oauth_client
from aequitas.api.auth.sessions import (
    COOKIE_MAX_AGE_SECONDS,
    COOKIE_NAME,
    session_cookie_secure,
    sign_session_id,
    unsign_session_id,
)
from aequitas.api.config import ApiConfig

router = APIRouter(tags=["auth"])

_DEV_USER_ID = "00000000-0000-0000-0000-000000000001"
_DEV_TENANT_ID = "00000000-0000-0000-0000-000000000002"


class SwitchTenantRequest(BaseModel):
    tenant_id: str


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "user"


@router.get("/auth/login/google")
async def login_google(request: Request):
    cfg = ApiConfig()
    if not cfg.google_client_id or not cfg.google_client_secret:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )
    oauth = get_google_oauth_client()
    redirect_uri = str(request.url_for("auth_callback_google"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/callback/google", name="auth_callback_google")
async def auth_callback_google(request: Request):
    oauth = get_google_oauth_client()
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail="Google OAuth exchange failed"
        ) from exc

    userinfo = token.get("userinfo") or {}
    email = userinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")
    display_name = userinfo.get("name")
    provider_subject = userinfo.get("sub")
    if not provider_subject:
        raise HTTPException(status_code=400, detail="Google account has no subject")

    pool = await db.get_pool()
    user = await db.get_or_create_user(
        pool,
        email=email,
        display_name=display_name,
        provider="google",
        provider_subject=provider_subject,
    )

    memberships = await db.list_memberships_for_user(pool, user_id=str(user["id"]))
    if not memberships:
        slug_base = _slugify(email.split("@")[0])
        tenant = await db.create_tenant(
            pool,
            name=f"{display_name or email}'s Workspace",
            slug=f"{slug_base}-{str(user['id'])[:8]}",
        )
        await db.create_membership(
            pool,
            user_id=str(user["id"]),
            tenant_id=str(tenant["id"]),
            role="admin",
        )
        active_tenant_id = str(tenant["id"])
        await db.get_or_create_profile(
            pool, user_id=str(user["id"]), display_name=display_name
        )
    else:
        active_tenant_id = str(memberships[0]["tenant_id"])

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=COOKIE_MAX_AGE_SECONDS)
    session = await db.create_session(
        pool,
        user_id=str(user["id"]),
        tenant_id=active_tenant_id,
        expires_at=expires_at,
    )

    cfg = ApiConfig()
    frontend_origin = cfg.frontend_url.rstrip("/")
    response = RedirectResponse(url=f"{frontend_origin}/dashboard")
    response.set_cookie(
        COOKIE_NAME,
        sign_session_id(str(session["id"])),
        httponly=True,
        secure=session_cookie_secure(),
        samesite="lax",
        max_age=COOKIE_MAX_AGE_SECONDS,
        path="/",
    )
    return response


@router.post("/auth/logout")
async def logout(request: Request):
    cookie_value = request.cookies.get(COOKIE_NAME)
    if cookie_value is not None:
        session_id = unsign_session_id(cookie_value)
        if session_id is not None and session_id != "dev-session":
            try:
                pool = await db.get_pool()
                await db.delete_session(pool, session_id=session_id)
            except Exception:
                pass

    response = JSONResponse({"status": "ok"})
    response.delete_cookie(COOKIE_NAME, path="/")
    return response


@router.get("/auth/me")
async def me(session: dict = Depends(require_session)) -> dict:
    # Dev-bypass synthetic session — no DB rows required.
    if session["session_id"] == "dev-session":
        return {
            "user": {
                "id": session["user_id"],
                "email": "dev@localhost",
                "display_name": "Dev User",
            },
            "active_tenant": {
                "id": session["tenant_id"],
                "name": "Dev Workspace",
                "slug": "dev-workspace",
            },
            "role": session["role"],
            "memberships": [
                {
                    "tenant_id": session["tenant_id"],
                    "tenant_name": "Dev Workspace",
                    "tenant_slug": "dev-workspace",
                    "role": session["role"],
                }
            ],
        }

    pool = await db.get_pool()
    memberships = await db.list_memberships_for_user(pool, user_id=session["user_id"])
    user_row = await db._fetch_user(pool, user_id=session["user_id"])
    active = next(
        (m for m in memberships if str(m["tenant_id"]) == session["tenant_id"]),
        None,
    )
    return {
        "user": {
            "id": session["user_id"],
            "email": user_row["email"],
            "display_name": user_row["display_name"],
        },
        "active_tenant": {
            "id": session["tenant_id"],
            "name": active["tenant_name"] if active else None,
            "slug": active["tenant_slug"] if active else None,
        },
        "role": session["role"],
        "memberships": [
            {
                "tenant_id": str(m["tenant_id"]),
                "tenant_name": m["tenant_name"],
                "tenant_slug": m["tenant_slug"],
                "role": m["role"],
            }
            for m in memberships
        ],
    }


@router.post("/session/switch-tenant")
async def switch_tenant(
    body: SwitchTenantRequest, session: dict = Depends(require_session)
) -> dict:
    if session["session_id"] == "dev-session":
        # Synthetic dev session has only the fixed tenant.
        if body.tenant_id != session["tenant_id"]:
            raise HTTPException(status_code=403, detail="Not a member of this tenant")
        return {"status": "ok", "active_tenant_id": body.tenant_id}

    pool = await db.get_pool()
    membership = await db.get_membership(
        pool, user_id=session["user_id"], tenant_id=body.tenant_id
    )
    if membership is None:
        raise HTTPException(status_code=403, detail="Not a member of this tenant")
    await db.update_session_tenant(
        pool, session_id=session["session_id"], tenant_id=body.tenant_id
    )
    return {"status": "ok", "active_tenant_id": body.tenant_id}
