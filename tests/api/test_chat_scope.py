"""No models, network calls, live databases or warehouse writes."""

from pathlib import Path

import pytest
from fastapi import HTTPException

from aequitas.api.services.chat_scope import current_chat_scope


@pytest.mark.parametrize(
    "context",
    [
        {"country": "unknown"},
        {"country": "netherlands", "mode": "all"},
    ],
)
def test_rejects_country_or_mode_without_index(context: dict[str, object]) -> None:
    with pytest.raises(HTTPException):
        current_chat_scope(context)


def test_rejects_dated_context_without_relabelling_current_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aequitas.warehouse import packs

    monkeypatch.setattr(packs, "resolve_pack", lambda *_: {"current": False})
    with pytest.raises(HTTPException, match="Historical-network answers"):
        current_chat_scope({"country": "ireland", "pack": "2020-01-01"})


def test_explicit_current_date_requires_live_warehouse(monkeypatch: pytest.MonkeyPatch) -> None:
    from aequitas.api import deps
    from aequitas.warehouse import packs

    monkeypatch.setattr(packs, "resolve_pack", lambda *_: {"current": True})
    monkeypatch.setattr(deps, "_live_path", lambda *_: Path("/tmp/live.duckdb"))
    monkeypatch.setattr(packs, "warehouse_for_pack", lambda *_: Path("/tmp/live.duckdb"))
    assert current_chat_scope({"country": "ireland", "pack": "2026-08-13"}) == "ireland"
    monkeypatch.setattr(packs, "warehouse_for_pack", lambda *_: Path("/tmp/other.duckdb"))
    with pytest.raises(HTTPException):
        current_chat_scope({"country": "ireland", "pack": "2026-08-13"})
