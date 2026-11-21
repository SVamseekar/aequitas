"""API configuration — loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from aequitas.core.datastore import data_dir


def _env_path(var: str, rel: str) -> Path:
    """Explicit env var wins; else ``rel`` under the data dir."""
    explicit = os.environ.get(var, "").strip()
    return Path(explicit) if explicit else data_dir() / rel


@dataclass
class ApiConfig:
    db_path: Path = field(
        default_factory=lambda: _env_path("AEQUITAS_DB_PATH", "aequitas.duckdb")
    )
    ireland_db_path: Path = field(
        default_factory=lambda: _env_path("AEQUITAS_IE_DB_PATH", "aequitas_ireland.duckdb")
    )
    netherlands_db_path: Path = field(
        default_factory=lambda: _env_path("AEQUITAS_NL_DB_PATH", "aequitas_netherlands.duckdb")
    )
    france_db_path: Path = field(
        default_factory=lambda: _env_path("AEQUITAS_FR_DB_PATH", "aequitas_france.duckdb")
    )
    faiss_index_path: Path = field(
        default_factory=lambda: _env_path("AEQUITAS_FAISS_INDEX", "faiss_index.bin")
    )
    faiss_metadata_path: Path = field(
        default_factory=lambda: _env_path("AEQUITAS_FAISS_METADATA", "faiss_metadata.json")
    )
    ireland_faiss_index_path: Path = field(
        default_factory=lambda: _env_path("AEQUITAS_IE_FAISS_INDEX", "ireland/faiss_index.bin")
    )
    ireland_faiss_metadata_path: Path = field(
        default_factory=lambda: _env_path(
            "AEQUITAS_IE_FAISS_METADATA", "ireland/faiss_metadata.json"
        )
    )
    france_faiss_index_path: Path = field(
        default_factory=lambda: _env_path("AEQUITAS_FR_FAISS_INDEX", "france/faiss_index.bin")
    )
    france_faiss_metadata_path: Path = field(
        default_factory=lambda: _env_path(
            "AEQUITAS_FR_FAISS_METADATA", "france/faiss_metadata.json"
        )
    )
    netherlands_faiss_index_path: Path = field(
        default_factory=lambda: _env_path("AEQUITAS_NL_FAISS_INDEX", "netherlands/faiss_index.bin")
    )
    netherlands_faiss_metadata_path: Path = field(
        default_factory=lambda: _env_path(
            "AEQUITAS_NL_FAISS_METADATA", "netherlands/faiss_metadata.json"
        )
    )
    gemini_api_key: str = field(
        default_factory=lambda: os.environ.get("GEMINI_API_KEY", "")
    )
    cors_origins: list[str] = field(
        default_factory=lambda: os.environ.get(
            "AEQUITAS_CORS_ORIGINS", "http://localhost:5173"
        ).split(",")
    )
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL", "postgresql://localhost/aequitas"
        )
    )
    session_secret: str = field(
        default_factory=lambda: os.environ.get("SESSION_SECRET", "")
    )
    google_client_id: str = field(
        default_factory=lambda: os.environ.get("GOOGLE_CLIENT_ID", "")
    )
    google_client_secret: str = field(
        default_factory=lambda: os.environ.get("GOOGLE_CLIENT_SECRET", "")
    )
    brevo_api_key: str = field(
        default_factory=lambda: os.environ.get("BREVO_API_KEY", "")
    )
    frontend_url: str = field(
        default_factory=lambda: os.environ.get(
            "FRONTEND_URL", "http://localhost:5173"
        )
    )
    api_public_url: str = field(
        default_factory=lambda: os.environ.get(
            "API_PUBLIC_URL", "http://localhost:8000"
        )
    )
