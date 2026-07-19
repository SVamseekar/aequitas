"""Google OAuth login/callback/logout and session-tenant-switch routes."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from aequitas.api.auth import db
from aequitas.api.auth.dependencies import require_admin, require_session
from aequitas.api.auth.email import send_invite_email
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


class CreateInviteRequest(BaseModel):
    email: str
    role: str = "member"


class UpdateRoleRequest(BaseModel):
    role: str


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
    pool = await db.get_pool()
    try:
        memberships = await db.list_memberships_for_user(
            pool, user_id=session["user_id"]
        )
        user_row = await db.get_user(pool, user_id=session["user_id"])
    except Exception:
        memberships = []
        user_row = None

    if user_row is None and session["session_id"] == "dev-session":
        user_row = {
            "id": session["user_id"],
            "email": "dev@localhost",
            "display_name": "Dev User",
        }
    if not memberships and session["session_id"] == "dev-session":
        memberships = [
            {
                "tenant_id": session["tenant_id"],
                "tenant_name": "Dev Workspace",
                "tenant_slug": "dev-workspace",
                "role": session["role"],
            }
        ]

    if user_row is None:
        raise HTTPException(status_code=401, detail="User not found")

    active = next(
        (m for m in memberships if str(m["tenant_id"]) == session["tenant_id"]),
        None,
    )
    return {
        "user": {
            "id": session["user_id"],
            "email": user_row["email"],
            "display_name": user_row.get("display_name"),
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
    pool = await db.get_pool()
    membership = await db.get_membership(
        pool, user_id=session["user_id"], tenant_id=body.tenant_id
    )
    if membership is None:
        raise HTTPException(status_code=403, detail="Not a member of this tenant")
    if session["session_id"] != "dev-session":
        await db.update_session_tenant(
            pool, session_id=session["session_id"], tenant_id=body.tenant_id
        )
    return {"status": "ok", "active_tenant_id": body.tenant_id}


@router.post("/tenants/{tenant_id}/invites")
async def create_invite(
    tenant_id: str,
    body: CreateInviteRequest,
    session: dict = Depends(require_admin),
) -> dict:
    if body.role not in ("admin", "member"):
        raise HTTPException(status_code=400, detail="role must be 'admin' or 'member'")

    pool = await db.get_pool()
    membership = await db.get_membership(
        pool, user_id=session["user_id"], tenant_id=tenant_id
    )
    if membership is None or membership["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")

    token = db.generate_invite_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    invite = await db.create_invite(
        pool,
        tenant_id=tenant_id,
        email=body.email,
        role=body.role,
        token=token,
        expires_at=expires_at,
    )
    await db.write_audit_log(
        pool,
        tenant_id=tenant_id,
        actor_user_id=session["user_id"],
        action="invite_created",
        target_user_id=None,
        metadata={"invited_email": body.email, "role": body.role},
    )

    cfg = ApiConfig()
    frontend_origin = cfg.frontend_url.rstrip("/")
    link = f"{frontend_origin}/invite/{token}"

    tenant_row = await db._fetch_tenant(pool, tenant_id=tenant_id)
    tenant_name = tenant_row["name"] if tenant_row else "Workspace"
    await send_invite_email(
        to_email=body.email, tenant_name=tenant_name, invite_link=link
    )

    return {"token": token, "link": link, "invite_id": str(invite["id"])}


@router.get("/invites/{token}")
async def get_invite(token: str) -> dict:
    pool = await db.get_pool()
    invite = await db.get_invite_by_token(pool, token=token)
    if invite is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite["accepted_at"] is not None:
        raise HTTPException(status_code=410, detail="Invite already accepted")
    expires_at = invite["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Invite expired")

    tenant_row = await db._fetch_tenant(pool, tenant_id=str(invite["tenant_id"]))
    return {
        "tenant_name": tenant_row["name"] if tenant_row else None,
        "role": invite["role"],
    }


@router.post("/invites/{token}/accept")
async def accept_invite_route(
    token: str, session: dict = Depends(require_session)
) -> dict:
    pool = await db.get_pool()
    invite = await db.get_invite_by_token(pool, token=token)
    if invite is None:
        raise HTTPException(status_code=404, detail="Invite not found")

    accepted = await db.accept_invite(pool, token=token)
    if accepted is None:
        raise HTTPException(
            status_code=410, detail="Invite already accepted or expired"
        )

    existing = await db.get_membership(
        pool, user_id=session["user_id"], tenant_id=str(invite["tenant_id"])
    )
    if existing is None:
        await db.create_membership(
            pool,
            user_id=session["user_id"],
            tenant_id=str(invite["tenant_id"]),
            role=invite["role"],
        )
    await db.write_audit_log(
        pool,
        tenant_id=str(invite["tenant_id"]),
        actor_user_id=session["user_id"],
        action="invite_accepted",
        target_user_id=session["user_id"],
        metadata={"invited_email": invite["email"], "role": invite["role"]},
    )
    return {"status": "ok", "tenant_id": str(invite["tenant_id"])}


@router.get("/tenants/{tenant_id}/members")
async def list_tenant_members(
    tenant_id: str, session: dict = Depends(require_admin)
) -> list[dict]:
    pool = await db.get_pool()
    members = await db.list_members_for_tenant(pool, tenant_id=tenant_id)
    return [
        {
            "user_id": str(m["user_id"]),
            "email": m["email"],
            "display_name": m["display_name"],
            "role": m["role"],
            "created_at": m["created_at"].isoformat()
            if hasattr(m["created_at"], "isoformat")
            else m["created_at"],
        }
        for m in members
    ]


@router.delete("/tenants/{tenant_id}/members/{user_id}")
async def remove_tenant_member(
    tenant_id: str,
    user_id: str,
    session: dict = Depends(require_admin),
) -> dict:
    pool = await db.get_pool()
    membership = await db.get_membership(
        pool, user_id=user_id, tenant_id=tenant_id
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")

    if membership["role"] == "admin":
        admin_count = await db.count_admins(pool, tenant_id=tenant_id)
        if admin_count <= 1:
            raise HTTPException(
                status_code=400, detail="Cannot remove the last admin of a tenant"
            )

    await db.remove_membership(pool, user_id=user_id, tenant_id=tenant_id)
    await db.write_audit_log(
        pool,
        tenant_id=tenant_id,
        actor_user_id=session["user_id"],
        action="member_removed",
        target_user_id=user_id,
        metadata={},
    )
    return {"status": "ok"}


@router.patch("/tenants/{tenant_id}/members/{user_id}/role")
async def update_member_role(
    tenant_id: str,
    user_id: str,
    body: UpdateRoleRequest,
    session: dict = Depends(require_admin),
) -> dict:
    if body.role not in ("admin", "member"):
        raise HTTPException(status_code=400, detail="role must be 'admin' or 'member'")

    pool = await db.get_pool()
    membership = await db.get_membership(
        pool, user_id=user_id, tenant_id=tenant_id
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")

    old_role = membership["role"]
    if old_role == "admin" and body.role != "admin":
        admin_count = await db.count_admins(pool, tenant_id=tenant_id)
        if admin_count <= 1:
            raise HTTPException(
                status_code=400, detail="Cannot demote the last admin of a tenant"
            )

    updated = await db.update_membership_role(
        pool, user_id=user_id, tenant_id=tenant_id, role=body.role
    )
    await db.write_audit_log(
        pool,
        tenant_id=tenant_id,
        actor_user_id=session["user_id"],
        action="role_changed",
        target_user_id=user_id,
        metadata={"old_role": old_role, "new_role": body.role},
    )
    return {
        "status": "ok",
        "user_id": user_id,
        "role": updated["role"] if updated else body.role,
    }


@router.get("/tenants/{tenant_id}/audit-log")
async def get_audit_log(
    tenant_id: str, session: dict = Depends(require_admin)
) -> list[dict]:
    pool = await db.get_pool()
    entries = await db.list_audit_log(pool, tenant_id=tenant_id)
    result = []
    for e in entries:
        result.append(
            {
                "id": str(e["id"]),
                "tenant_id": str(e["tenant_id"]),
                "actor_user_id": str(e["actor_user_id"]),
                "action": e["action"],
                "target_user_id": str(e["target_user_id"])
                if e["target_user_id"]
                else None,
                "metadata": e["metadata"],
                "created_at": e["created_at"].isoformat()
                if hasattr(e["created_at"], "isoformat")
                else e["created_at"],
            }
        )
    return result
