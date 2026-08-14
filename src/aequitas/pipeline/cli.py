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
    aequitas refresh     — Unattended NaPTAN+BODS download + rebuild
    aequitas schedule-refresh — Install monthly macOS launchd job
"""

import click
from loguru import logger


@click.group()
def main() -> None:
    """Aequitas data pipeline — raw government data to DuckDB warehouse."""


@main.command()
@click.option("--country", default="england", help="england | ireland")
def ingest(country: str) -> None:
    """Stage 1: Load and filter raw data sources."""
    if country == "ireland":
        from aequitas.ireland.pipeline import run_ireland_pack
        run_ireland_pack()
        return
    from aequitas.pipeline._stages import run_ingestion
    run_ingestion()


@main.command()
@click.option("--country", default="england", help="england | ireland")
def process(country: str) -> None:
    """Stage 2: Spatial joins, dedup, demographics, route geometry, service quality."""
    if country == "ireland":
        from aequitas.ireland.pipeline import run_ireland_pack
        run_ireland_pack()
        return
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
@click.option("--country", default="england", help="england | ireland")
def warehouse(country: str) -> None:
    """Stage 5: Build DuckDB warehouse from processed Parquet + narratives."""
    if country == "ireland":
        from aequitas.ireland.pipeline import run_ireland_pack
        run_ireland_pack(skip_download=True)
        return
    from aequitas.pipeline._stages import run_warehouse
    run_warehouse()


@main.command()
def validate() -> None:
    """Stage 6: Run ground truth validation gates against Phase 0 locked values."""
    from aequitas.pipeline._stages import run_validation
    run_validation()


@main.command()
@click.option("--country", default="england", help="england | ireland")
def rag(country: str) -> None:
    """Build FAISS index for RAG chatbot (England or Ireland narratives)."""
    from aequitas.pipeline._stages import run_rag_index
    run_rag_index(country=country)


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


@main.command()
@click.option("--skip-download", is_flag=True)
def ireland(skip_download: bool) -> None:
    """Build the Republic of Ireland pack (TFI × HP 2022 × CSO SA)."""
    from aequitas.ireland.pipeline import run_ireland_pack
    from aequitas.ireland.bands import write_ireland_bands

    dest = run_ireland_pack(skip_download=skip_download)
    write_ireland_bands()
    logger.info("Ireland pack ready: {}", dest)



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


@main.command()
@click.option("--skip-download", is_flag=True, help="Rebuild from files already in data/raw/")
@click.option(
    "--force",
    is_flag=True,
    help="Ignore the 25-day freshness skip (still uses a lock so two runs cannot overlap).",
)
@click.option("--country", default="england", help="england | ireland")
def refresh(skip_download: bool, force: bool, country: str) -> None:
    """Download latest network (BODS or TFI), write a dated pack, swap current if sanity passes."""
    from aequitas.pipeline.refresh import run_refresh

    code = run_refresh(
        skip_download=skip_download,
        min_interval_days=0 if force else 25,
        country=country,
    )
    if code != 0:
        raise SystemExit(code)


@main.command("schedule-refresh")
def schedule_refresh() -> None:
    """Install a monthly launchd job (1st of month, 02:00) on this Mac."""
    from aequitas.core.config import PipelineConfig
    from aequitas.pipeline.refresh import install_schedule

    path = install_schedule(PipelineConfig().project_root)
    logger.info("Scheduled. Leave this Mac powered on overnight on the 1st. Plist: {}", path)
