"""DuckDB warehouse builder — creates and populates the pre-built warehouse.

Loads processed Parquet files → creates DuckDB tables → warehouse is
read-only after build. All analytics pre-computed at build time.

Usage::

    from aequitas.core.config import PipelineConfig
    from aequitas.warehouse.builder import build_warehouse

    cfg = PipelineConfig()
    build_warehouse(cfg)
"""

from pathlib import Path

import duckdb
from loguru import logger

from aequitas.core.config import PipelineConfig
from aequitas.warehouse.schema import ANALYTICS_PARQUET_SOURCES, CORE_TABLES


def build_warehouse(cfg: PipelineConfig, overwrite: bool = False) -> None:
    """Create and populate the DuckDB warehouse from processed Parquet files.

    Steps:
    1. Create/open DuckDB file at cfg.warehouse_path
    2. Create all core table schemas
    3. Load analytics Parquet files as DuckDB tables
    4. (Precompute phase handled by warehouse.precompute module)

    Args:
        cfg: Pipeline configuration with warehouse_path and processed_dir.
        overwrite: If True, drop and recreate existing tables.
    """
    warehouse_path = cfg.warehouse_path
    warehouse_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Building warehouse at {warehouse_path}")
    conn = duckdb.connect(str(warehouse_path))

    try:
        # Step 1: Create core tables
        for table_name, ddl in CORE_TABLES.items():
            if overwrite:
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.execute(ddl)
            logger.debug(f"Created core table: {table_name}")

        # Step 2: Load analytics Parquet tables
        for table_name, parquet_rel_path in ANALYTICS_PARQUET_SOURCES.items():
            parquet_path = Path(parquet_rel_path)
            if not parquet_path.is_absolute():
                # Try relative to project root and to processed_dir
                candidate = cfg.processed_dir / parquet_path.name
                if not candidate.exists():
                    candidate = Path(parquet_rel_path)
            else:
                candidate = parquet_path

            if overwrite:
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")

            if candidate.exists():
                conn.execute(
                    f"CREATE TABLE IF NOT EXISTS {table_name} AS "
                    f"SELECT * FROM read_parquet('{candidate}')"
                )
                n = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                logger.info(f"Loaded {table_name}: {n:,} rows from {candidate.name}")
            else:
                # Create empty table placeholder — filled later by precompute
                logger.warning(
                    f"Parquet not found for {table_name} at {candidate} — "
                    "creating placeholder (run pipeline first)"
                )

        conn.execute("CHECKPOINT")
        logger.info("Warehouse build complete")

    finally:
        conn.close()


def get_connection(cfg: PipelineConfig) -> duckdb.DuckDBPyConnection:
    """Open a read-only connection to the warehouse.

    Args:
        cfg: Pipeline configuration with warehouse_path.

    Returns:
        DuckDB connection (read_only=True).
    """
    return duckdb.connect(str(cfg.warehouse_path), read_only=True)
