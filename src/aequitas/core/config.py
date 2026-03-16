"""Pipeline configuration — paths, thresholds, filter space."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from aequitas.core.types import RegionCode

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@dataclass
class PipelineConfig:
    """Central configuration for all pipeline stages."""

    project_root: Path = _PROJECT_ROOT
    raw_dir: Path = field(default_factory=lambda: _PROJECT_ROOT / "data" / "raw")
    audit_dir: Path = field(default_factory=lambda: _PROJECT_ROOT / "data" / "audit")
    processed_dir: Path = field(default_factory=lambda: _PROJECT_ROOT / "data" / "processed")
    warehouse_path: Path = field(default_factory=lambda: _PROJECT_ROOT / "data" / "aequitas.duckdb")

    # Validation thresholds
    min_match_rate: float = 0.95
    stops_per_1000_max: float = 30.0
    routes_sanity_max: int = 50_000

    # BODS chunking
    stop_times_chunk_size: int = 1_000_000
    shapes_chunk_size: int = 500_000

    # RAG / API
    faiss_index_path: Path = field(default_factory=lambda: Path("data/faiss_index.bin"))
    faiss_metadata_path: Path = field(default_factory=lambda: Path("data/faiss_metadata.json"))
    gemini_api_key: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""))
    api_cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:5173"])

    def filter_combinations(self) -> list[tuple[str, str]]:
        """All 30 filter combinations: (region, urban_rural)."""
        regions = ["all"] + [r.value for r in RegionCode]
        area_types = ["all", "urban", "rural"]
        return [(r, a) for r in regions for a in area_types]
