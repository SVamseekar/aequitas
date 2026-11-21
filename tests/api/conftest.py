from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def isolated_search_indexes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep every API fixture, including custom clients, off user-owned RAG indexes."""
    monkeypatch.setenv("AEQUITAS_FAISS_INDEX", str(tmp_path / "england.faiss"))
    monkeypatch.setenv("AEQUITAS_FAISS_METADATA", str(tmp_path / "england.json"))
    for country in ("IE", "NL", "FR"):
        monkeypatch.setenv(f"AEQUITAS_{country}_FAISS_INDEX", str(tmp_path / f"{country}.faiss"))
        monkeypatch.setenv(f"AEQUITAS_{country}_FAISS_METADATA", str(tmp_path / f"{country}.json"))


@pytest.fixture
def api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Create a test client with a temporary DuckDB."""
    import duckdb

    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        CREATE TABLE section_results (
            region VARCHAR,
            urban_rural VARCHAR,
            section_id VARCHAR,
            stats JSON,
            chart_data JSON,
            narrative VARCHAR,
            PRIMARY KEY (region, urban_rural, section_id)
        )
    """)
    conn.execute("""
        INSERT INTO section_results VALUES
        ('all', 'all', 'f1_gini', '{"gini": 0.5741}', '{"type": "lorenz_curve"}',
         '**Gini is 0.574.**')
    """)
    conn.execute("""
        CREATE TABLE provenance (
            metric_id VARCHAR PRIMARY KEY,
            value DOUBLE,
            formula VARCHAR,
            inputs JSON,
            source_files VARCHAR[]
        )
    """)
    conn.execute("""
        INSERT INTO provenance VALUES
        ('gini_national', 0.5741, '1 - 2*AUC(lorenz)', '{}', ARRAY['equity.parquet'])
    """)
    conn.close()

    monkeypatch.setenv("AEQUITAS_DB_PATH", str(db_path))
    monkeypatch.setenv("AEQUITAS_FAISS_INDEX", str(tmp_path / "faiss.bin"))
    monkeypatch.setenv("AEQUITAS_FAISS_METADATA", str(tmp_path / "faiss_meta.json"))
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")

    from aequitas.api.app import create_app

    app = create_app()
    with TestClient(app) as client:
        yield client
