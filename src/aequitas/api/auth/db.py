"""asyncpg connection pool and query functions for the tenancy/auth schema."""
from __future__ import annotations

import asyncio
import json
import os
import secrets
from pathlib import Path

import asyncpg

_pool: asyncpg.Pool | None = None
_pool_loop_id: int | None = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )


async def get_pool() -> asyncpg.Pool:
    """Return a process-wide asyncpg pool, recreating it if the event loop changed.

    Pytest (and some ASGI test clients) can run different tests on different
    event loops; a pool bound to a closed loop raises on use, so we detect
    the loop change and recreate rather than reuse a dead pool.
    """
    global _pool, _pool_loop_id
    loop_id = id(asyncio.get_running_loop())
    if _pool is not None and _pool_loop_id != loop_id:
        try:
            await _pool.close()
        except Exception:
            pass
        _pool = None
        _pool_loop_id = None
    if _pool is None:
        database_url = os.environ["DATABASE_URL"]
        _pool = await asyncpg.create_pool(
            database_url, min_size=1, max_size=10, init=_init_connection
        )
        _pool_loop_id = loop_id
    return _pool


async def run_migrations(pool: asyncpg.Pool) -> None:
    """Apply schema.sql — idempotent, safe to call on every app startup."""
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    sql = schema_path.read_text()
    async with pool.acquire() as conn:
        await conn.execute(sql)


async def get_or_create_user(
    pool: asyncpg.Pool,
    *,
    email: str,
    display_name: str | None,
    provider: str,
    provider_subject: str,
) -> dict:
    """Look up a user by OAuth identity, creating user + identity rows if new."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            identity = await conn.fetchrow(
                """
                SELECT user_id FROM oauth_identities
                WHERE provider = $1 AND provider_subject = $2
                """,
                provider,
                provider_subject,
            )
            if identity is not None:
                user_row = await conn.fetchrow(
                    "SELECT * FROM users WHERE id = $1", identity["user_id"]
                )
                return dict(user_row)

            user_row = await conn.fetchrow(
                """
                INSERT INTO users (email, display_name)
                VALUES ($1, $2)
                ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
                RETURNING *
                """,
                email,
                display_name,
            )
            await conn.execute(
                """
                INSERT INTO oauth_identities (user_id, provider, provider_subject)
                VALUES ($1, $2, $3)
                """,
                user_row["id"],
                provider,
                provider_subject,
            )
            return dict(user_row)


async def create_tenant(pool: asyncpg.Pool, *, name: str, slug: str) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO tenants (name, slug) VALUES ($1, $2) RETURNING *",
            name,
            slug,
        )
        return dict(row)


async def create_membership(
    pool: asyncpg.Pool, *, user_id: str, tenant_id: str, role: str
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO memberships (user_id, tenant_id, role)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            user_id,
            tenant_id,
            role,
        )
        return dict(row)


async def get_membership(
    pool: asyncpg.Pool, *, user_id: str, tenant_id: str
) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM memberships WHERE user_id = $1 AND tenant_id = $2",
            user_id,
            tenant_id,
        )
        return dict(row) if row is not None else None


async def list_memberships_for_user(pool: asyncpg.Pool, *, user_id: str) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.tenant_id, m.role, m.created_at, t.name AS tenant_name, t.slug AS tenant_slug
            FROM memberships m
            JOIN tenants t ON t.id = m.tenant_id
            WHERE m.user_id = $1
            ORDER BY m.created_at ASC
            """,
            user_id,
        )
        return [dict(r) for r in rows]


async def create_session(
    pool: asyncpg.Pool, *, user_id: str, tenant_id: str, expires_at
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO sessions (user_id, tenant_id, expires_at)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            user_id,
            tenant_id,
            expires_at,
        )
        return dict(row)


async def get_session(pool: asyncpg.Pool, *, session_id: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM sessions WHERE id = $1", session_id)
        return dict(row) if row is not None else None


async def update_session_tenant(
    pool: asyncpg.Pool, *, session_id: str, tenant_id: str
) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE sessions SET tenant_id = $1 WHERE id = $2 RETURNING *",
            tenant_id,
            session_id,
        )
        return dict(row) if row is not None else None


async def delete_session(pool: asyncpg.Pool, *, session_id: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM sessions WHERE id = $1", session_id)


async def create_invite(
    pool: asyncpg.Pool, *, tenant_id: str, email: str, role: str, token: str, expires_at
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO invites (tenant_id, email, role, token, expires_at)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            tenant_id,
            email,
            role,
            token,
            expires_at,
        )
        return dict(row)


async def get_invite_by_token(pool: asyncpg.Pool, *, token: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM invites WHERE token = $1", token)
        return dict(row) if row is not None else None


async def accept_invite(pool: asyncpg.Pool, *, token: str) -> dict | None:
    """Mark an invite accepted. Returns None if missing, already accepted, or expired."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE invites
            SET accepted_at = now()
            WHERE token = $1 AND accepted_at IS NULL AND expires_at > now()
            RETURNING *
            """,
            token,
        )
        return dict(row) if row is not None else None


async def remove_membership(pool: asyncpg.Pool, *, user_id: str, tenant_id: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM memberships WHERE user_id = $1 AND tenant_id = $2",
            user_id,
            tenant_id,
        )


async def update_membership_role(
    pool: asyncpg.Pool, *, user_id: str, tenant_id: str, role: str
) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE memberships SET role = $1
            WHERE user_id = $2 AND tenant_id = $3
            RETURNING *
            """,
            role,
            user_id,
            tenant_id,
        )
        return dict(row) if row is not None else None


async def write_audit_log(
    pool: asyncpg.Pool,
    *,
    tenant_id: str,
    actor_user_id: str,
    action: str,
    target_user_id: str | None,
    metadata: dict | None,
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO audit_log (tenant_id, actor_user_id, action, target_user_id, metadata)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            tenant_id,
            actor_user_id,
            action,
            target_user_id,
            metadata,
        )
        return dict(row)


async def list_audit_log(pool: asyncpg.Pool, *, tenant_id: str) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM audit_log WHERE tenant_id = $1 ORDER BY created_at DESC",
            tenant_id,
        )
        return [dict(r) for r in rows]


def generate_invite_token() -> str:
    """Generate a URL-safe random invite token."""
    return secrets.token_urlsafe(32)


async def get_tenant(pool: asyncpg.Pool, *, tenant_id: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM tenants WHERE id = $1", tenant_id)
        return dict(row) if row is not None else None


async def _fetch_tenant(pool: asyncpg.Pool, *, tenant_id: str) -> dict | None:
    return await get_tenant(pool, tenant_id=tenant_id)


async def get_user(pool: asyncpg.Pool, *, user_id: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        return dict(row) if row is not None else None


async def _fetch_user(pool: asyncpg.Pool, *, user_id: str) -> dict:
    row = await get_user(pool, user_id=user_id)
    if row is None:
        raise KeyError(f"user not found: {user_id}")
    return row


async def get_or_create_profile(
    pool: asyncpg.Pool, *, user_id: str, display_name: str | None = None
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO profiles (user_id, display_name)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE
              SET display_name = COALESCE(EXCLUDED.display_name, profiles.display_name)
            RETURNING *
            """,
            user_id,
            display_name,
        )
        return dict(row)


async def create_profile(
    pool: asyncpg.Pool, *, user_id: str, display_name: str | None = None
) -> dict:
    return await get_or_create_profile(
        pool, user_id=user_id, display_name=display_name
    )


async def get_profile(pool: asyncpg.Pool, *, user_id: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM profiles WHERE user_id = $1", user_id)
        return dict(row) if row is not None else None


async def update_profile_policy_interests(
    pool: asyncpg.Pool, *, user_id: str, policy_interests: list[str]
) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE profiles
            SET policy_interests = $1, updated_at = now()
            WHERE user_id = $2
            RETURNING *
            """,
            policy_interests,
            user_id,
        )
        return dict(row) if row is not None else None


async def count_admins(pool: asyncpg.Pool, *, tenant_id: str) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) AS n FROM memberships WHERE tenant_id = $1 AND role = 'admin'",
            tenant_id,
        )
        return int(row["n"]) if row else 0


async def list_members(pool: asyncpg.Pool, *, tenant_id: str) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.user_id, m.role, m.created_at, u.email, u.display_name
            FROM memberships m
            JOIN users u ON u.id = m.user_id
            WHERE m.tenant_id = $1
            ORDER BY m.created_at ASC
            """,
            tenant_id,
        )
        return [dict(r) for r in rows]


async def list_members_for_tenant(pool: asyncpg.Pool, *, tenant_id: str) -> list[dict]:
    return await list_members(pool, tenant_id=tenant_id)


# ---------------------------------------------------------------------------
# Tenant-scoped application data (conversations, analyses, notes, regions)
# ---------------------------------------------------------------------------


async def list_conversations(pool: asyncpg.Pool, *, tenant_id: str) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM conversations
            WHERE tenant_id = $1
            ORDER BY updated_at DESC
            LIMIT 50
            """,
            tenant_id,
        )
        return [dict(r) for r in rows]


async def create_conversation(
    pool: asyncpg.Pool, *, tenant_id: str, user_id: str, title: str
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO conversations (tenant_id, user_id, title)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            tenant_id,
            user_id,
            title,
        )
        return dict(row)


async def get_conversation(
    pool: asyncpg.Pool, *, tenant_id: str, conversation_id: str
) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM conversations WHERE id = $1 AND tenant_id = $2",
            conversation_id,
            tenant_id,
        )
        return dict(row) if row is not None else None


async def update_conversation_title(
    pool: asyncpg.Pool, *, tenant_id: str, conversation_id: str, title: str
) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE conversations
            SET title = $1, updated_at = now()
            WHERE id = $2 AND tenant_id = $3
            RETURNING *
            """,
            title,
            conversation_id,
            tenant_id,
        )
        return dict(row) if row is not None else None


async def touch_conversation(
    pool: asyncpg.Pool, *, tenant_id: str, conversation_id: str
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE conversations SET updated_at = now()
            WHERE id = $1 AND tenant_id = $2
            """,
            conversation_id,
            tenant_id,
        )


async def delete_conversation(
    pool: asyncpg.Pool, *, tenant_id: str, conversation_id: str
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM conversations WHERE id = $1 AND tenant_id = $2",
            conversation_id,
            tenant_id,
        )


async def list_messages(
    pool: asyncpg.Pool,
    *,
    tenant_id: str,
    conversation_id: str,
    offset: int = 0,
    limit: int = 100,
) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM messages
            WHERE conversation_id = $1 AND tenant_id = $2
            ORDER BY created_at ASC
            OFFSET $3 LIMIT $4
            """,
            conversation_id,
            tenant_id,
            offset,
            limit,
        )
        return [dict(r) for r in rows]


async def create_message(
    pool: asyncpg.Pool,
    *,
    tenant_id: str,
    conversation_id: str,
    user_id: str,
    role: str,
    content: str,
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO messages (conversation_id, tenant_id, user_id, role, content)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            conversation_id,
            tenant_id,
            user_id,
            role,
            content,
        )
        return dict(row)


async def list_saved_analyses(pool: asyncpg.Pool, *, tenant_id: str) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM saved_analyses
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            """,
            tenant_id,
        )
        return [dict(r) for r in rows]


async def create_saved_analysis(
    pool: asyncpg.Pool,
    *,
    tenant_id: str,
    user_id: str,
    title: str,
    content: str,
    section_id: str | None = None,
    dimension: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO saved_analyses
              (tenant_id, user_id, title, content, section_id, dimension, tags)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
            """,
            tenant_id,
            user_id,
            title,
            content,
            section_id,
            dimension,
            tags or [],
        )
        return dict(row)


async def delete_saved_analysis(
    pool: asyncpg.Pool, *, tenant_id: str, analysis_id: str
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM saved_analyses WHERE id = $1 AND tenant_id = $2",
            analysis_id,
            tenant_id,
        )


async def list_policy_notes(pool: asyncpg.Pool, *, tenant_id: str) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM policy_notes
            WHERE tenant_id = $1
            ORDER BY updated_at DESC
            """,
            tenant_id,
        )
        return [dict(r) for r in rows]


async def create_policy_note(
    pool: asyncpg.Pool,
    *,
    tenant_id: str,
    user_id: str,
    dimension: str,
    region: str,
    stance: str | None,
    thesis: str,
    critique: str | None = None,
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO policy_notes
              (tenant_id, user_id, dimension, region, stance, thesis, critique)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
            """,
            tenant_id,
            user_id,
            dimension,
            region,
            stance,
            thesis,
            critique,
        )
        return dict(row)


async def update_policy_note(
    pool: asyncpg.Pool,
    *,
    tenant_id: str,
    note_id: str,
    dimension: str | None = None,
    region: str | None = None,
    stance: str | None = None,
    thesis: str | None = None,
    critique: str | None = None,
) -> dict | None:
    existing = None
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT * FROM policy_notes WHERE id = $1 AND tenant_id = $2",
            note_id,
            tenant_id,
        )
        if existing is None:
            return None
        row = await conn.fetchrow(
            """
            UPDATE policy_notes SET
              dimension = COALESCE($1, dimension),
              region = COALESCE($2, region),
              stance = COALESCE($3, stance),
              thesis = COALESCE($4, thesis),
              critique = COALESCE($5, critique),
              updated_at = now()
            WHERE id = $6 AND tenant_id = $7
            RETURNING *
            """,
            dimension,
            region,
            stance,
            thesis,
            critique,
            note_id,
            tenant_id,
        )
        return dict(row) if row is not None else None


async def delete_policy_note(
    pool: asyncpg.Pool, *, tenant_id: str, note_id: str
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM policy_notes WHERE id = $1 AND tenant_id = $2",
            note_id,
            tenant_id,
        )


async def list_saved_regions(pool: asyncpg.Pool, *, tenant_id: str) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM saved_regions
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            """,
            tenant_id,
        )
        return [dict(r) for r in rows]


async def create_saved_region(
    pool: asyncpg.Pool,
    *,
    tenant_id: str,
    user_id: str,
    region_code: str,
    region_name: str,
    notes: str | None = None,
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO saved_regions
              (tenant_id, user_id, region_code, region_name, notes)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            tenant_id,
            user_id,
            region_code,
            region_name,
            notes,
        )
        return dict(row)


async def delete_saved_region(
    pool: asyncpg.Pool, *, tenant_id: str, region_id: str
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM saved_regions WHERE id = $1 AND tenant_id = $2",
            region_id,
            tenant_id,
        )
