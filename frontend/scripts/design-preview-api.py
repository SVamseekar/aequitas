"""Local analytics preview without migrations, model downloads or invented auth.

From repository root: uv run --no-sync python frontend/scripts/design-preview-api.py
Warehouse access retains the app's read-only dependencies. Lifespan is off;
authenticated tenant/OAuth workflows cannot be accepted using this preview.
"""
from pathlib import Path

import uvicorn

from aequitas.api.app import app
from aequitas.api.deps import _state

root = Path(__file__).resolve().parents[2] / "data"
_state.update(
    db_path=root / "aequitas.duckdb",
    ie_db_path=root / "aequitas_ireland.duckdb",
    nl_db_path=root / "aequitas_netherlands.duckdb",
    fr_db_path=root / "aequitas_france.duckdb",
)
uvicorn.run(app, host="127.0.0.1", port=8000, lifespan="off", log_level="warning")
