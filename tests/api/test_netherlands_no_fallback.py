"""country=netherlands must not fall back to England numbers."""

from fastapi.testclient import TestClient

from aequitas.api.app import create_app


def test_unknown_pack_404() -> None:
    client = TestClient(create_app())
    r = client.get("/api/score", params={"country": "netherlands", "pack": "2099-01-01"})
    assert r.status_code == 404
    assert "england" not in r.text.lower() or "not falling back" in r.text.lower()


def test_time_unknown_pack_404() -> None:
    client = TestClient(create_app())
    r = client.get("/api/time", params={"country": "netherlands", "pack": "2099-01-01"})
    assert r.status_code == 404


def test_france_still_empty() -> None:
    client = TestClient(create_app())
    r = client.get("/api/score", params={"country": "france"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("score") is None
