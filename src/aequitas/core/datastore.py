"""Where Aequitas data lives — the only module that knows.

Every other module asks this one for a path. Nothing else builds
``<project_root>/data/...`` by hand.

Two settings (environment variables):

``AEQUITAS_DATA_DIR``
    Local working copy of the data. Default ``<project_root>/data``.
    Code always reads and writes here.

``AEQUITAS_DATA_REMOTE``
    Optional durable store the local copy syncs with. Empty = local only
    (the behaviour before this module existed). Supported forms:

    - ``hf://datasets/<owner>/<repo>`` (optionally ``@<revision>``)
    - ``file:///abs/path`` — a plain directory (tests, mounted buckets)

    Add a new backend by implementing :class:`Remote` and registering it in
    :func:`remote_from_url`. No caller changes.

Runtime reads stay local, so a remote never sits in a request path: the
API pulls the ``app`` profile once at startup, then serves from disk.
"""

from __future__ import annotations

import fnmatch
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from loguru import logger

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent

ENV_DATA_DIR = "AEQUITAS_DATA_DIR"
ENV_DATA_REMOTE = "AEQUITAS_DATA_REMOTE"

# Never synced: partial writes, runtime state that may hold user identifiers, logs.
EXCLUDE: tuple[str, ...] = (
    "*.tmp",
    "*.wal",
    "*.lock",
    "chat_rate_limit.sqlite",
    "logs/*",
    "*.DS_Store",
)

# Named sets of files. Patterns are relative to the data dir (fnmatch, ``*``
# crosses ``/``).
PROFILES: dict[str, tuple[str, ...]] = {
    # Everything the API reads at runtime: warehouses, FAISS, processed
    # tables, packs, ops rollups. Excludes raw inputs and old backups.
    "app": (
        "*.duckdb",
        "faiss_index.bin",
        "faiss_metadata.json",
        "*/faiss_index.bin",
        "*/faiss_metadata.json",
        "processed/*",
        "audit/*",
        "packs/*",
        "ops/*",
        "models/*",
        "refresh_state*.json",
    ),
    "raw": ("raw/*",),
    "all": ("*",),
}


def data_dir(project_root: Path | None = None) -> Path:
    """Local data directory.

    ``AEQUITAS_DATA_DIR`` wins. Otherwise ``<project_root>/data``, where
    ``project_root`` defaults to the repository root. Passing a
    ``project_root`` keeps test fixtures that build a fake tree working.
    """
    override = os.environ.get(ENV_DATA_DIR, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (project_root or PROJECT_ROOT) / "data"


def data_path(*parts: str | Path, project_root: Path | None = None) -> Path:
    """Path under the local data dir. Does not fetch anything."""
    return data_dir(project_root).joinpath(*parts)


def _excluded(rel: str) -> bool:
    return any(fnmatch.fnmatch(rel, pat) for pat in EXCLUDE)


def matches(rel: str, patterns: tuple[str, ...] | list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, pat) for pat in patterns) and not _excluded(rel)


def profile_patterns(profile: str) -> tuple[str, ...]:
    try:
        return PROFILES[profile]
    except KeyError:
        raise ValueError(f"Unknown data profile {profile!r}; known: {sorted(PROFILES)}") from None


# ── Remote backends ──────────────────────────────────────────────────────────


class Remote(Protocol):
    """A durable copy of the data dir. Paths are POSIX, relative to its root."""

    url: str

    def list_files(self) -> list[str]: ...

    def pull(self, rel_paths: list[str], dest: Path) -> list[Path]: ...

    def push(self, src: Path, rel_paths: list[str], message: str) -> None: ...


@dataclass
class LocalDirRemote:
    """A plain directory used as the remote (tests, mounted buckets)."""

    root: Path
    url: str = ""

    def list_files(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(
            p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file()
        )

    def pull(self, rel_paths: list[str], dest: Path) -> list[Path]:
        out: list[Path] = []
        for rel in rel_paths:
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.root / rel, target)
            out.append(target)
        return out

    def push(self, src: Path, rel_paths: list[str], message: str) -> None:
        for rel in rel_paths:
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src / rel, target)


@dataclass
class HuggingFaceRemote:
    """A Hugging Face repo (dataset by default). Auth: ``HF_TOKEN`` or ``hf auth login``."""

    repo_id: str
    repo_type: str = "dataset"
    revision: str | None = None
    url: str = ""

    def list_files(self) -> list[str]:
        from huggingface_hub import HfApi

        files = HfApi().list_repo_files(
            self.repo_id, repo_type=self.repo_type, revision=self.revision
        )
        return sorted(f for f in files if f != ".gitattributes")

    def pull(self, rel_paths: list[str], dest: Path) -> list[Path]:
        if not rel_paths:
            return []
        from huggingface_hub import snapshot_download

        dest.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id=self.repo_id,
            repo_type=self.repo_type,
            revision=self.revision,
            local_dir=dest,
            allow_patterns=rel_paths,
        )
        return [dest / rel for rel in rel_paths]

    def push(self, src: Path, rel_paths: list[str], message: str) -> None:
        if not rel_paths:
            return
        from huggingface_hub import HfApi

        HfApi().upload_folder(
            repo_id=self.repo_id,
            repo_type=self.repo_type,
            revision=self.revision,
            folder_path=src,
            allow_patterns=rel_paths,
            commit_message=message,
        )


def remote_from_url(url: str) -> Remote:
    """Build a backend from a URL. Raise on unknown schemes — never guess."""
    url = url.strip()
    if url.startswith("hf://"):
        rest = url[len("hf://") :]
        revision: str | None = None
        if "@" in rest:
            rest, revision = rest.split("@", 1)
        parts = rest.strip("/").split("/")
        kinds = {"datasets": "dataset", "models": "model", "spaces": "space"}
        if len(parts) == 3 and parts[0] in kinds:
            repo_type, repo_id = kinds[parts[0]], f"{parts[1]}/{parts[2]}"
        elif len(parts) == 2:
            repo_type, repo_id = "dataset", f"{parts[0]}/{parts[1]}"
        else:
            raise ValueError(f"Bad Hugging Face remote {url!r}; want hf://datasets/<owner>/<repo>")
        return HuggingFaceRemote(repo_id=repo_id, repo_type=repo_type, revision=revision, url=url)
    if url.startswith("file://"):
        return LocalDirRemote(root=Path(url[len("file://") :]).expanduser(), url=url)
    raise ValueError(f"Unsupported data remote {url!r}; supported: hf://, file://")


def get_remote() -> Remote | None:
    """The configured remote, or ``None`` when running local-only."""
    url = os.environ.get(ENV_DATA_REMOTE, "").strip()
    return remote_from_url(url) if url else None


# ── Sync operations ──────────────────────────────────────────────────────────


@dataclass
class SyncReport:
    remote: str
    matched: int
    transferred: list[str]

    def log(self, verb: str) -> None:
        logger.info(
            "Data {}: {} of {} matching files via {}",
            verb,
            len(self.transferred),
            self.matched,
            self.remote,
        )


def _local_files(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def pull(
    patterns: tuple[str, ...] | list[str],
    *,
    remote: Remote | None = None,
    dest: Path | None = None,
    overwrite: bool = False,
) -> SyncReport:
    """Copy matching remote files into the local data dir.

    By default only files missing locally are fetched, so a warm cache costs
    one listing call.
    """
    remote = remote or get_remote()
    if remote is None:
        raise RuntimeError(f"No data remote configured; set {ENV_DATA_REMOTE}")
    dest = dest or data_dir()
    wanted = [rel for rel in remote.list_files() if matches(rel, patterns)]
    todo = wanted if overwrite else [rel for rel in wanted if not (dest / rel).exists()]
    remote.pull(todo, dest)
    report = SyncReport(remote=remote.url, matched=len(wanted), transferred=todo)
    report.log("pull")
    return report


def push(
    patterns: tuple[str, ...] | list[str],
    *,
    remote: Remote | None = None,
    src: Path | None = None,
    message: str = "data: sync from aequitas",
) -> SyncReport:
    """Upload matching local files to the remote. Excluded files never leave."""
    remote = remote or get_remote()
    if remote is None:
        raise RuntimeError(f"No data remote configured; set {ENV_DATA_REMOTE}")
    src = src or data_dir()
    todo = [rel for rel in _local_files(src) if matches(rel, patterns)]
    remote.push(src, todo, message)
    report = SyncReport(remote=remote.url, matched=len(todo), transferred=todo)
    report.log("push")
    return report


def ensure_profile(profile: str) -> SyncReport | None:
    """Fill missing local files for ``profile`` from the remote, if one is set.

    Local-only setups return ``None`` and change nothing. A remote failure is
    logged and swallowed: the caller still has whatever is on disk, and its
    own "file not found" handling stays in charge.
    """
    remote = get_remote()
    if remote is None:
        return None
    try:
        return pull(profile_patterns(profile), remote=remote)
    except Exception as exc:  # network, auth, missing repo
        logger.error("Data pull for profile {!r} from {} failed: {}", profile, remote.url, exc)
        return None
