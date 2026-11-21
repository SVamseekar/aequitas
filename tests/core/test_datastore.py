"""DataStore: path resolution, remote parsing, pull/push, API config wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

from aequitas.core import datastore
from aequitas.core.datastore import (
    HuggingFaceRemote,
    LocalDirRemote,
    data_dir,
    ensure_profile,
    matches,
    profile_patterns,
    pull,
    push,
    remote_from_url,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(datastore.ENV_DATA_DIR, raising=False)
    monkeypatch.delenv(datastore.ENV_DATA_REMOTE, raising=False)


def _write(root: Path, rel: str, text: str = "x") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


# ── path resolution ──────────────────────────────────────────────────────────


def test_data_dir_defaults_to_repo_data() -> None:
    assert data_dir() == datastore.PROJECT_ROOT / "data"


def test_data_dir_respects_project_root(tmp_path: Path) -> None:
    assert data_dir(tmp_path) == tmp_path / "data"


def test_env_overrides_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(datastore.ENV_DATA_DIR, str(tmp_path / "cache"))
    assert data_dir() == (tmp_path / "cache").resolve()
    assert data_dir(Path("/elsewhere")) == (tmp_path / "cache").resolve()


def test_pipeline_and_api_config_follow_data_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aequitas.api.config import ApiConfig
    from aequitas.core.config import PipelineConfig

    monkeypatch.setenv(datastore.ENV_DATA_DIR, str(tmp_path))
    root = tmp_path.resolve()
    cfg = PipelineConfig()
    assert cfg.raw_dir == root / "raw"
    assert cfg.processed_dir == root / "processed"
    assert cfg.warehouse_path == root / "aequitas.duckdb"
    api = ApiConfig()
    assert api.db_path == root / "aequitas.duckdb"
    assert api.france_db_path == root / "aequitas_france.duckdb"
    assert api.ireland_faiss_index_path == root / "ireland" / "faiss_index.bin"


def test_explicit_api_env_var_still_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from aequitas.api.config import ApiConfig

    monkeypatch.setenv(datastore.ENV_DATA_DIR, str(tmp_path))
    monkeypatch.setenv("AEQUITAS_DB_PATH", "/custom/en.duckdb")
    assert ApiConfig().db_path == Path("/custom/en.duckdb")


# ── remote URL parsing ───────────────────────────────────────────────────────


def test_hf_url_full_form() -> None:
    remote = remote_from_url("hf://datasets/owner/repo@v1")
    assert isinstance(remote, HuggingFaceRemote)
    assert (remote.repo_id, remote.repo_type, remote.revision) == ("owner/repo", "dataset", "v1")


def test_hf_url_short_form_defaults_to_dataset() -> None:
    remote = remote_from_url("hf://owner/repo")
    assert isinstance(remote, HuggingFaceRemote)
    assert (remote.repo_id, remote.repo_type, remote.revision) == ("owner/repo", "dataset", None)


def test_file_url(tmp_path: Path) -> None:
    remote = remote_from_url(f"file://{tmp_path}")
    assert isinstance(remote, LocalDirRemote)
    assert remote.root == tmp_path


@pytest.mark.parametrize("url", ["s3://bucket/x", "hf://onlyowner", "nonsense"])
def test_unknown_or_bad_url_raises(url: str) -> None:
    with pytest.raises(ValueError):
        remote_from_url(url)


# ── matching ─────────────────────────────────────────────────────────────────


def test_app_profile_takes_runtime_files_not_raw_or_backups() -> None:
    app = profile_patterns("app")
    assert matches("aequitas.duckdb", app)
    assert matches("ireland/faiss_index.bin", app)
    assert matches("processed/reach/lsoa_access_bands.parquet", app)
    assert not matches("raw/bods/gtfs.zip", app)
    assert not matches("aequitas.duckdb.bak", app)


def test_excluded_files_never_match_even_with_all() -> None:
    everything = profile_patterns("all")
    for rel in ("x.duckdb.tmp", "a.wal", "chat_rate_limit.sqlite", "logs/refresh.log"):
        assert not matches(rel, everything)


def test_unknown_profile_raises() -> None:
    with pytest.raises(ValueError):
        profile_patterns("nope")


# ── pull / push round trip ───────────────────────────────────────────────────


def test_push_then_pull_round_trip(tmp_path: Path) -> None:
    local, store, fresh = tmp_path / "local", tmp_path / "store", tmp_path / "fresh"
    _write(local, "aequitas.duckdb", "warehouse")
    _write(local, "processed/a.parquet", "p")
    _write(local, "raw/big.zip", "raw")
    _write(local, "chat_rate_limit.sqlite", "secret")
    remote = LocalDirRemote(root=store, url="file://store")

    pushed = push(profile_patterns("all"), remote=remote, src=local)
    assert sorted(pushed.transferred) == ["aequitas.duckdb", "processed/a.parquet", "raw/big.zip"]
    assert not (store / "chat_rate_limit.sqlite").exists()

    pulled = pull(profile_patterns("app"), remote=remote, dest=fresh)
    assert sorted(pulled.transferred) == ["aequitas.duckdb", "processed/a.parquet"]
    assert (fresh / "aequitas.duckdb").read_text() == "warehouse"
    assert not (fresh / "raw").exists()


def test_pull_skips_files_already_local_unless_overwrite(tmp_path: Path) -> None:
    store, local = tmp_path / "store", tmp_path / "local"
    _write(store, "aequitas.duckdb", "remote")
    _write(local, "aequitas.duckdb", "local")
    remote = LocalDirRemote(root=store)

    assert pull(("*",), remote=remote, dest=local).transferred == []
    assert (local / "aequitas.duckdb").read_text() == "local"

    assert pull(("*",), remote=remote, dest=local, overwrite=True).transferred == [
        "aequitas.duckdb"
    ]
    assert (local / "aequitas.duckdb").read_text() == "remote"


def test_pull_without_remote_raises(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        pull(("*",), dest=tmp_path)


# ── ensure_profile (API startup) ─────────────────────────────────────────────


def test_ensure_profile_is_noop_without_remote() -> None:
    assert ensure_profile("app") is None


def test_ensure_profile_fills_data_dir_from_env_remote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, local = tmp_path / "store", tmp_path / "local"
    _write(store, "aequitas_ireland.duckdb", "ie")
    _write(store, "raw/x.zip", "raw")
    monkeypatch.setenv(datastore.ENV_DATA_DIR, str(local))
    monkeypatch.setenv(datastore.ENV_DATA_REMOTE, f"file://{store}")

    report = ensure_profile("app")
    assert report is not None and report.transferred == ["aequitas_ireland.duckdb"]
    assert (local / "aequitas_ireland.duckdb").exists()
    assert not (local / "raw").exists()


def test_ensure_profile_logs_and_survives_remote_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Broken(LocalDirRemote):
        def list_files(self) -> list[str]:
            raise ConnectionError("offline")

    monkeypatch.setattr(datastore, "get_remote", lambda: Broken(root=Path("/nowhere")))
    assert ensure_profile("app") is None
