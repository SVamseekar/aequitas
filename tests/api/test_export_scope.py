"""Dimension PDF scope cannot silently borrow England or the current date."""

from collections.abc import Iterator
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aequitas.api.auth.dependencies import require_session
from aequitas.api.deps import get_db
from aequitas.api.routers import export


@pytest.fixture
def scoped_export(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, Mock]]:
    from aequitas.warehouse import packs

    app = FastAPI()
    app.include_router(export.router, prefix="/api")
    app.dependency_overrides[require_session] = lambda: {"tenant_id": "unit", "user_id": "unit"}
    app.dependency_overrides[get_db] = lambda: None
    builder = Mock(return_value=b"%PDF-isolated-fixture")
    monkeypatch.setattr(export, "_build_pdf", builder)
    monkeypatch.setattr(packs, "resolve_pack", lambda *_: {"current": False})
    with TestClient(app) as client:
        yield client, builder


@pytest.mark.parametrize(
    "query,status",
    [
        ("country=ireland", 400),
        ("country=france", 400),
        ("country=netherlands", 400),
        ("country=unknown", 404),
        ("pack=2020-01-01", 400),
        ("as_of=2020-01-01", 400),
        ("mode=all", 400),
    ],
)
def test_unsupported_dimension_pdf_scope_never_generates_england_report(
    scoped_export: tuple[TestClient, Mock], query: str, status: int
) -> None:
    client, builder = scoped_export
    response = client.get(f"/api/export/equity?{query}")
    assert response.status_code == status
    builder.assert_not_called()


def test_existing_current_england_pdf_remains_compatible(
    scoped_export: tuple[TestClient, Mock],
) -> None:
    client, builder = scoped_export
    response = client.get("/api/export/equity?region=E12000005&urban_rural=urban")
    assert response.status_code == 200
    builder.assert_called_once_with("equity", [], "E12000005", "urban")
