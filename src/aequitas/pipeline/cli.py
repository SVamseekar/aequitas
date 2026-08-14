"""Aequitas pipeline CLI.

Usage::

    aequitas ingest      — Stage 1: Load and filter raw data sources
    aequitas process     — Stage 2: Spatial joins, dedup, demographics, geometry, SQI
    aequitas analytics   — Stage 3: Equity, ML, accessibility, economic, policy
    aequitas intelligence — Stage 4: InsightEngine narratives
    aequitas warehouse   — Stage 5: Build DuckDB from Parquet + narratives
    aequitas validate    — Stage 6: Ground truth validation gates
    aequitas run         — Run all stages end-to-end
    aequitas reach       — r5py 15/30/45 destination counts (after process)
    aequitas studio      — apply a StudioPatch (walk-to-stop; r5py if present)
"""

import click
from loguru import logger


@click.group()
def main() -> None:
    """Aequitas data pipeline — raw government data to DuckDB warehouse."""


@main.command()
def ingest() -> None:
    """Stage 1: Load and filter raw data sources."""
    from aequitas.pipeline._stages import run_ingestion
    run_ingestion()


@main.command()
def process() -> None:
    """Stage 2: Spatial joins, dedup, demographics, route geometry, service quality."""
    from aequitas.pipeline._stages import run_processing
    run_processing()


@main.command()
def analytics() -> None:
    """Stage 3: Equity, ML, accessibility, economic appraisal, policy synthesis."""
    from aequitas.pipeline._stages import run_analytics
    run_analytics()


@main.command()
def intelligence() -> None:
    """Stage 4: Run InsightEngine — generate evidence-gated narratives."""
    from aequitas.pipeline._stages import run_intelligence
    run_intelligence()


@main.command()
def warehouse() -> None:
    """Stage 5: Build DuckDB warehouse from processed Parquet + narratives."""
    from aequitas.pipeline._stages import run_warehouse
    run_warehouse()


@main.command()
def validate() -> None:
    """Stage 6: Run ground truth validation gates against Phase 0 locked values."""
    from aequitas.pipeline._stages import run_validation
    run_validation()


@main.command()
def rag() -> None:
    """Build FAISS index for RAG chatbot."""
    from aequitas.pipeline._stages import run_rag_index
    run_rag_index()


@main.command()
@click.option("--force", is_flag=True, help="Recompute even if cache is newer than GTFS+PBF.")
@click.option("--region", default=None, help="ITL1 code batch (e.g. E12000005 West Midlands).")
def reach(force: bool, region: str | None) -> None:
    """Precompute 15/30/45-minute destination counts with r5py + R5 (Java)."""
    from aequitas.pipeline._stages import run_reach

    run_reach(force=force, region=region)


@main.command()
@click.option("--patch", "patch_path", default=None, help="Path to a StudioPatch JSON file.")
@click.option("--force", is_flag=True, help="Rebuild even if this patch hash is cached.")
def studio(patch_path: str | None, force: bool) -> None:
    """Apply a StudioPatch. Walk-to-stop without r5py; frequency needs Java 17 + PBF."""
    from aequitas.pipeline._stages import run_studio

    run_studio(patch_path=patch_path, force=force)


@main.command("run")
def run_all() -> None:
    """Run all pipeline stages end-to-end."""
    from aequitas.pipeline._stages import (
        run_ingestion,
        run_processing,
        run_analytics,
        run_reach,
        run_intelligence,
        run_warehouse,
        run_validation,
        run_rag_index,
    )

    stages = [
        ("ingest", run_ingestion),
        ("process", run_processing),
        ("analytics", run_analytics),
        ("reach", run_reach),
        ("intelligence", run_intelligence),
        ("warehouse", run_warehouse),
        ("validate", run_validation),
        ("rag_index", run_rag_index),
    ]

    for name, fn in stages:
        logger.info("=== Stage: {} ===", name)
        fn()
        logger.info("=== {} complete ===", name)

    logger.info("Pipeline complete. Warehouse: data/aequitas.duckdb")
