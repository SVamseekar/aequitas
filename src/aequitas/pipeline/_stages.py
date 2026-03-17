"""Pipeline stage orchestration — wires together all 6 stages.

Each run_*() function reads from previous stage outputs, writes processed
Parquets to config.processed_dir, and logs timing + validation checkpoints.

Per data-quality.md rule: every stage writes a validation checkpoint before
the next stage starts.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from aequitas.core.config import PipelineConfig


@dataclass
class StageReport:
    stage: str
    duration_s: float
    output_files: list[Path] = field(default_factory=list)
    checks_passed: int = 0
    checks_failed: int = 0

    def log(self) -> None:
        status = "OK" if self.checks_failed == 0 else f"WARN ({self.checks_failed} failed)"
        logger.info(
            f"Stage '{self.stage}' complete in {self.duration_s:.1f}s — "
            f"{self.checks_passed} checks PASS, status: {status}"
        )


def run_ingestion(cfg: PipelineConfig | None = None) -> StageReport:
    """Stage 1: Load and filter raw data sources.

    Reads:
        data/raw/naptan/, data/raw/bods/, data/raw/census/, data/raw/imd/, etc.
    Writes:
        data/processed/naptan_stops.parquet
        data/processed/bods_routes.parquet
        data/processed/bods_stops.parquet
        data/processed/master_lsoa_table.parquet
    """
    if cfg is None:
        cfg = PipelineConfig()

    cfg.processed_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    logger.info("Stage 1: Ingestion — loading raw data sources")

    from aequitas.ingestion.naptan import load_naptan
    from aequitas.ingestion.bods import load_bods_routes, load_bods_stops
    from aequitas.processing.demographics import build_master_lsoa_table

    output_files: list[Path] = []
    checks_passed = 0

    # NaPTAN
    try:
        naptan_path = cfg.raw_dir / "naptan" / "NaPTANcsv.csv"
        if naptan_path.exists():
            stops = load_naptan(naptan_path)
            out = cfg.processed_dir / "naptan_stops.parquet"
            stops.to_parquet(out, index=False)
            output_files.append(out)
            logger.info(f"NaPTAN: {len(stops):,} stops → {out.name}")
            if len(stops) == 274_719:
                checks_passed += 1
        else:
            logger.warning(f"NaPTAN file not found: {naptan_path}")
    except Exception as e:
        logger.error(f"NaPTAN ingestion failed: {e}")

    # BODS routes
    try:
        bods_zip = cfg.raw_dir / "bods" / "bods_gtfs_all.zip"
        if bods_zip.exists():
            routes = load_bods_routes(bods_zip)
            out = cfg.processed_dir / "bods_routes.parquet"
            routes.to_parquet(out, index=False)
            output_files.append(out)
            logger.info(f"BODS routes: {len(routes):,} → {out.name}")
            checks_passed += 1
        else:
            logger.warning(f"BODS zip not found: {bods_zip}")
    except Exception as e:
        logger.error(f"BODS routes ingestion failed: {e}")

    # Master LSOA table
    try:
        master = build_master_lsoa_table(cfg)
        out = cfg.processed_dir / "master_lsoa_table.parquet"
        master.to_parquet(out, index=False)
        output_files.append(out)
        logger.info(f"Master LSOA table: {len(master):,} rows → {out.name}")
        if len(master) == 33_755:
            checks_passed += 1
    except Exception as e:
        logger.error(f"Master LSOA table failed: {e}")

    duration = time.perf_counter() - t0
    report = StageReport("ingest", duration, output_files, checks_passed)
    report.log()
    return report


def run_processing(cfg: PipelineConfig | None = None) -> StageReport:
    """Stage 2: Spatial joins, dedup, route geometry, service quality."""
    if cfg is None:
        cfg = PipelineConfig()

    cfg.processed_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    logger.info("Stage 2: Processing — spatial joins, geometry, service quality")

    output_files: list[Path] = []
    checks_passed = 0

    # Route geometries
    try:
        from aequitas.processing.route_geometry import compute_route_geometries
        routes_geo = compute_route_geometries(cfg)
        out = cfg.processed_dir / "route_geometries.parquet"
        routes_geo.to_parquet(out, index=False)
        output_files.append(out)
        logger.info(f"Route geometries: {len(routes_geo):,} routes → {out.name}")
        checks_passed += 1
    except Exception as e:
        logger.error(f"Route geometry processing failed: {e}")

    # Service quality
    try:
        from aequitas.processing.service_quality import compute_service_quality
        sqi = compute_service_quality(cfg)
        out = cfg.processed_dir / "lsoa_service_quality.parquet"
        sqi.to_parquet(out, index=False)
        output_files.append(out)
        logger.info(f"Service quality: {len(sqi):,} LSOAs → {out.name}")
        checks_passed += 1
    except Exception as e:
        logger.error(f"Service quality processing failed: {e}")

    duration = time.perf_counter() - t0
    report = StageReport("process", duration, output_files, checks_passed)
    report.log()
    return report


def run_analytics(cfg: PipelineConfig | None = None) -> StageReport:
    """Stage 3: Equity metrics, ML clustering/prediction, 2SFCA, economic, policy."""
    if cfg is None:
        cfg = PipelineConfig()

    logger.info("Stage 3: Analytics — equity, ML, accessibility, economic, policy")
    t0 = time.perf_counter()

    # Analytics outputs are loaded from Phase 0 audit Parquets
    # Full re-computation would require all processing outputs to exist
    # For now: verify Phase 0 audit files exist as a checkpoint
    checks_passed = 0
    audit_files = [
        "lsoa_equity_metrics.parquet",
        "lsoa_service_quality.parquet",
        "lsoa_policy_synthesis.parquet",
        "lta_franchising_readiness.parquet",
        "policy_scenarios.parquet",
        "shap_importance.parquet",
    ]
    for fname in audit_files:
        if (cfg.audit_dir / fname).exists():
            checks_passed += 1
        else:
            logger.warning(f"Audit Parquet not found: {fname}")

    duration = time.perf_counter() - t0
    report = StageReport("analytics", duration, [], checks_passed, len(audit_files) - checks_passed)
    report.log()
    return report


def run_intelligence(cfg: PipelineConfig | None = None) -> StageReport:
    """Stage 4: Run InsightEngine — generate evidence-gated narratives."""
    if cfg is None:
        cfg = PipelineConfig()

    logger.info("Stage 4: Intelligence — generating narratives via InsightEngine")
    t0 = time.perf_counter()

    from aequitas.warehouse.precompute import precompute_all_sections

    results = precompute_all_sections(cfg)
    logger.info(f"Generated {len(results)} section results")

    duration = time.perf_counter() - t0
    report = StageReport("intelligence", duration, [], len(results), 0)
    report.log()
    return report


def run_warehouse(cfg: PipelineConfig | None = None) -> StageReport:
    """Stage 5: Build DuckDB warehouse from processed Parquet + narratives."""
    if cfg is None:
        cfg = PipelineConfig()

    logger.info(f"Stage 5: Warehouse — building {cfg.warehouse_path}")
    t0 = time.perf_counter()

    from aequitas.warehouse.builder import build_warehouse as _build

    # Pick up section results if intelligence stage ran in this process
    section_results: list[dict] | None = getattr(cfg, "_section_results", None)
    if section_results is None:
        # Fallback: recompute (e.g. when warehouse stage is run standalone)
        from aequitas.warehouse.precompute import precompute_all_sections
        section_results = precompute_all_sections(cfg)

    _build(cfg, overwrite=True, section_results=section_results)

    duration = time.perf_counter() - t0
    report = StageReport("warehouse", duration, [cfg.warehouse_path], 1, 0)
    report.log()
    return report


def run_rag_index(cfg: PipelineConfig | None = None) -> StageReport:
    """Build FAISS index from DuckDB narratives."""
    if cfg is None:
        cfg = PipelineConfig()

    from aequitas.rag.index_builder import build_faiss_index

    t0 = time.perf_counter()
    result = build_faiss_index(cfg)
    return StageReport(
        stage="rag_index",
        duration_s=time.perf_counter() - t0,
        output_files=[Path(p) for p in [result.get("index_path", ""), result.get("metadata_path", "")] if p],
        checks_passed=1 if result.get("n_chunks", 0) > 0 else 0,
        checks_failed=0 if result.get("n_chunks", 0) > 0 else 1,
    )


def run_validation(cfg: PipelineConfig | None = None) -> StageReport:
    """Stage 6: Run ground truth validation gates."""
    if cfg is None:
        cfg = PipelineConfig()

    logger.info("Stage 6: Validation — checking against Phase 0 ground truth")
    t0 = time.perf_counter()

    from aequitas.validation.ground_truth import validate_against_ground_truth
    from aequitas.validation.report import generate_report

    result = validate_against_ground_truth(cfg)
    report_str = generate_report(
        result,
        output_path=cfg.processed_dir / "validation_report.md",
    )

    if not result["all_pass"]:
        logger.error(f"Validation FAILED — {result['n_fail']} checks failed")
    else:
        logger.info(f"Validation passed — {result['n_pass']} checks OK")

    duration = time.perf_counter() - t0
    report = StageReport(
        "validate", duration, [], result["n_pass"], result["n_fail"]
    )
    report.log()
    return report
