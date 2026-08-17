"""On-disk ops rollups. Never written into the static DuckDB warehouses."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COUNTRIES = ("england", "ireland", "netherlands", "france")


def ops_dir(project_root: Path | None = None) -> Path:
    env = os.environ.get("AEQUITAS_OPS_DIR")
    if env:
        return Path(env)
    root = project_root or Path(__file__).resolve().parents[3]
    return root / "data" / "ops"


def rollup_path(country: str, project_root: Path | None = None) -> Path:
    return ops_dir(project_root) / country.lower() / "latest.json"


def write_rollup(country: str, payload: dict[str, Any], project_root: Path | None = None) -> Path:
    dest = rollup_path(country, project_root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return dest


def load_latest_rollup(country: str, project_root: Path | None = None) -> dict[str, Any] | None:
    path = rollup_path(country, project_root)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
