"""Isolated workspace-context contracts; no real Postgres or user records."""

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aequitas.api.auth import db
from aequitas.api.auth.dependencies import require_session
from aequitas.api.routers import conversations, policy_notes, saved_analyses, saved_regions

CONTEXT = {
    "country": "ireland",
    "page": "access",
    "query": {"region": "dublin", "pack": "2026-08-01", "view": "facilities"},
}


@pytest.fixture
def workspace_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    app = FastAPI()
    for router in (
        saved_analyses.router,
        policy_notes.router,
        saved_regions.router,
        conversations.router,
    ):
        app.include_router(router, prefix="/api")
    app.dependency_overrides[require_session] = lambda: {
        "tenant_id": "workspace-a",
        "user_id": "user-a",
    }
    monkeypatch.setattr(db, "get_pool", AsyncMock(return_value=object()))
    with TestClient(app) as client:
        yield client


def test_saved_analysis_context_and_tenant_are_forwarded(
    workspace_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    create = AsyncMock(return_value={"id": "record", "view_context": CONTEXT})
    monkeypatch.setattr(db, "create_saved_analysis", create)
    response = workspace_client.post(
        "/api/saved-analyses",
        json={
            "title": "Stored finding",
            "content": "Actual saved content",
            "view_context": CONTEXT,
        },
    )
    assert response.status_code == 201
    assert response.json()["view_context"] == CONTEXT
    assert create.await_args.kwargs["tenant_id"] == "workspace-a"
    assert create.await_args.kwargs["user_id"] == "user-a"
    assert create.await_args.kwargs["view_context"] == CONTEXT


def test_legacy_create_does_not_guess_country_or_date(
    workspace_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    create = AsyncMock(return_value={"id": "legacy", "view_context": None})
    monkeypatch.setattr(db, "create_saved_analysis", create)
    response = workspace_client.post(
        "/api/saved-analyses", json={"title": "Legacy", "content": "Text"}
    )
    assert response.status_code == 201
    assert response.json()["view_context"] is None
    assert "view_context" not in create.await_args.kwargs


@pytest.mark.parametrize(
    "context",
    [
        {**CONTEXT, "country": "unknown"},
        {**CONTEXT, "page": "https://example.org"},
        {**CONTEXT, "query": {"session_token": "not-allowed"}},
        {**CONTEXT, "query": {"region": "x" * 257}},
    ],
)
def test_context_rejects_unknown_countries_routes_and_secret_keys(
    workspace_client: TestClient, context: dict[str, object]
) -> None:
    response = workspace_client.post(
        "/api/saved-analyses",
        json={
            "title": "Invalid",
            "content": "Text",
            "view_context": context,
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "path,method,body,store",
    [
        (
            "/api/policy-notes",
            "post",
            {"dimension": "accessibility", "thesis": "Note"},
            "create_policy_note",
        ),
        (
            "/api/policy-notes/00000000-0000-0000-0000-000000000001",
            "patch",
            {"thesis": "Edited"},
            "update_policy_note",
        ),
        (
            "/api/saved-regions",
            "post",
            {"region_code": "dublin", "region_name": "Dublin"},
            "create_saved_region",
        ),
    ],
)
def test_note_and_region_context_keep_tenant_scope(
    workspace_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    method: str,
    body: dict[str, object],
    store: str,
) -> None:
    create = AsyncMock(return_value={"id": "record", "view_context": CONTEXT})
    monkeypatch.setattr(db, store, create)
    response = getattr(workspace_client, method)(path, json={**body, "view_context": CONTEXT})
    assert response.status_code in (200, 201)
    assert create.await_args.kwargs["tenant_id"] == "workspace-a"
    assert create.await_args.kwargs["view_context"] == CONTEXT


def test_new_context_does_not_relax_session_requirement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)
    app = FastAPI()
    app.include_router(saved_analyses.router, prefix="/api")
    with TestClient(app) as client:
        response = client.post(
            "/api/saved-analyses",
            json={
                "title": "Not signed in",
                "content": "Text",
                "view_context": CONTEXT,
            },
        )
    assert response.status_code == 401


def test_conversation_snapshot_uses_actual_messages_and_scope(
    workspace_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create = AsyncMock(return_value={"id": "conversation", "view_context": CONTEXT})
    monkeypatch.setattr(db, "create_conversation", create)
    messages = [
        {"role": "user", "content": "Question"},
        {"role": "assistant", "content": "Stored answer"},
    ]
    response = workspace_client.post(
        "/api/conversations",
        json={
            "title": "Question",
            "view_context": CONTEXT,
            "messages": messages,
        },
    )
    assert response.status_code == 201
    assert create.await_args.kwargs["messages"] == messages
    assert create.await_args.kwargs["tenant_id"] == "workspace-a"
    invalid = workspace_client.post(
        "/api/conversations",
        json={
            "title": "Invalid",
            "messages": [{"role": "system", "content": "Not accepted"}],
        },
    )
    assert invalid.status_code == 422


@pytest.mark.parametrize("sent", [False, True])
def test_invite_response_exposes_actual_delivery_result_without_sending(
    monkeypatch: pytest.MonkeyPatch, sent: bool
) -> None:
    from aequitas.api.auth.dependencies import require_admin
    from aequitas.api.routers import auth

    app = FastAPI()
    app.include_router(auth.router, prefix="/api")
    app.dependency_overrides[require_admin] = lambda: {
        "tenant_id": "workspace-a",
        "user_id": "user-a",
        "role": "admin",
    }
    monkeypatch.setattr(db, "get_pool", AsyncMock(return_value=object()))
    monkeypatch.setattr(db, "get_membership", AsyncMock(return_value={"role": "admin"}))
    monkeypatch.setattr(db, "create_invite", AsyncMock(return_value={"id": "unit-invite"}))
    monkeypatch.setattr(db, "write_audit_log", AsyncMock())
    monkeypatch.setattr(db, "_fetch_tenant", AsyncMock(return_value={"name": "Unit workspace"}))
    sender = AsyncMock(return_value=sent)
    monkeypatch.setattr(auth, "send_invite_email", sender)
    with TestClient(app) as client:
        response = client.post(
            "/api/tenants/workspace-a/invites",
            json={"email": "unit@example.test", "role": "member"},
        )
    assert response.status_code == 200
    assert response.json()["email_sent"] is sent
    assert sender.await_count == 1
