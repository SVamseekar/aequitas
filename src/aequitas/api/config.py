"""API configuration — loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ApiConfig:
    db_path: Path = field(
        default_factory=lambda: Path(os.environ.get("AEQUITAS_DB_PATH", "data/aequitas.duckdb"))
    )
    faiss_index_path: Path = field(
        default_factory=lambda: Path(os.environ.get("AEQUITAS_FAISS_INDEX", "data/faiss_index.bin"))
    )
    faiss_metadata_path: Path = field(
        default_factory=lambda: Path(os.environ.get("AEQUITAS_FAISS_METADATA", "data/faiss_metadata.json"))
    )
    gemini_api_key: str = field(
        default_factory=lambda: os.environ.get("GEMINI_API_KEY", "")
    )
    cors_origins: list[str] = field(
        default_factory=lambda: os.environ.get(
            "AEQUITAS_CORS_ORIGINS", "http://localhost:5173"
        ).split(",")
    )
