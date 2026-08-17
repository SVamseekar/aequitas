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
    ireland_db_path: Path = field(
        default_factory=lambda: Path(
            os.environ.get("AEQUITAS_IE_DB_PATH", "data/aequitas_ireland.duckdb")
        )
    )
    netherlands_db_path: Path = field(
        default_factory=lambda: Path(
            os.environ.get("AEQUITAS_NL_DB_PATH", "data/aequitas_netherlands.duckdb")
        )
    )
    france_db_path: Path = field(
        default_factory=lambda: Path(
            os.environ.get("AEQUITAS_FR_DB_PATH", "data/aequitas_france.duckdb")
        )
    )
    faiss_index_path: Path = field(
        default_factory=lambda: Path(os.environ.get("AEQUITAS_FAISS_INDEX", "data/faiss_index.bin"))
    )
    faiss_metadata_path: Path = field(
        default_factory=lambda: Path(os.environ.get("AEQUITAS_FAISS_METADATA", "data/faiss_metadata.json"))
    )
    ireland_faiss_index_path: Path = field(
        default_factory=lambda: Path(
            os.environ.get("AEQUITAS_IE_FAISS_INDEX", "data/ireland/faiss_index.bin")
        )
    )
    ireland_faiss_metadata_path: Path = field(
        default_factory=lambda: Path(
            os.environ.get("AEQUITAS_IE_FAISS_METADATA", "data/ireland/faiss_metadata.json")
        )
    )
    france_faiss_index_path: Path = field(
        default_factory=lambda: Path(
            os.environ.get("AEQUITAS_FR_FAISS_INDEX", "data/france/faiss_index.bin")
        )
    )
    france_faiss_metadata_path: Path = field(
        default_factory=lambda: Path(
            os.environ.get("AEQUITAS_FR_FAISS_METADATA", "data/france/faiss_metadata.json")
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
