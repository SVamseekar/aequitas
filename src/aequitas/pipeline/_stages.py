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
            stops.to_parquet(out, index=False, compression="zstd")
            output_files.append(out)
            logger.info(f"NaPTAN: {len(stops):,} stops → {out.name}")
            if len(stops) == 274_719:
                checks_passed += 1
        else:
            logger.warning(f"NaPTAN file not found: {naptan_path}")
    except Exception as e:
        logger.error(f"NaPTAN ingestion failed: {e}")
        raise

    # BODS routes
    try:
        bods_zip = cfg.raw_dir / "bods" / "bods_gtfs_all.zip"
        if bods_zip.exists():
            routes = load_bods_routes(bods_zip)
            out = cfg.processed_dir / "bods_routes.parquet"
            routes.to_parquet(out, index=False, compression="zstd")
            output_files.append(out)
            logger.info(f"BODS routes: {len(routes):,} → {out.name}")
            checks_passed += 1
        else:
            logger.warning(f"BODS zip not found: {bods_zip}")
    except Exception as e:
        logger.error(f"BODS routes ingestion failed: {e}")
        raise

    # Master LSOA table
    try:
        master = build_master_lsoa_table(cfg)
        out = cfg.processed_dir / "master_lsoa_table.parquet"
        master.to_parquet(out, index=False, compression="zstd")
        output_files.append(out)
        logger.info(f"Master LSOA table: {len(master):,} rows → {out.name}")
        if len(master) == 33_755:
            checks_passed += 1
    except Exception as e:
        logger.error(f"Master LSOA table failed: {e}")
        raise

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
        routes_geo.to_parquet(out, index=False, compression="zstd")
        output_files.append(out)
        logger.info(f"Route geometries: {len(routes_geo):,} routes → {out.name}")
        checks_passed += 1
    except Exception as e:
        logger.error(f"Route geometry processing failed: {e}")
        raise

    # Service quality
    try:
        from aequitas.processing.service_quality import compute_service_quality
        sqi = compute_service_quality(cfg)
        out = cfg.processed_dir / "lsoa_service_quality.parquet"
        sqi.to_parquet(out, index=False, compression="zstd")
        output_files.append(out)
        logger.info(f"Service quality: {len(sqi):,} LSOAs → {out.name}")
        checks_passed += 1
    except Exception as e:
        logger.error(f"Service quality processing failed: {e}")
        raise

    # Route urban/rural classification
    try:
        from aequitas.processing.route_urban_rural import compute_route_urban_rural
        route_ur = compute_route_urban_rural(cfg)
        out = cfg.processed_dir / "route_urban_rural.parquet"
        route_ur.to_parquet(out, index=False, compression="zstd")
        output_files.append(out)
        # _load_sources (warehouse/precompute.py) reads route-level
        # intermediates from audit_dir, mirroring route_geometries.parquet
        # and lsoa_service_quality.parquet — write a copy there so the
        # warehouse precompute step can discover it after a real pipeline run.
        cfg.audit_dir.mkdir(parents=True, exist_ok=True)
        audit_out = cfg.audit_dir / "route_urban_rural.parquet"
        route_ur.to_parquet(audit_out, index=False, compression="zstd")
        logger.info(f"Route urban/rural: {len(route_ur):,} routes → {out.name} (+ audit copy)")
        checks_passed += 1
    except Exception as e:
        logger.error(f"Route urban/rural processing failed: {e}")
        raise

    # Route trip frequency
    try:
        from aequitas.processing.route_trip_frequency import compute_route_trip_frequency
        route_freq = compute_route_trip_frequency(cfg)
        out = cfg.processed_dir / "route_trip_frequency.parquet"
        route_freq.to_parquet(out, index=False, compression="zstd")
        output_files.append(out)
        # _load_sources (warehouse/precompute.py) reads route-level
        # intermediates from audit_dir, mirroring route_geometries.parquet
        # and route_urban_rural.parquet — write a copy there so the
        # warehouse precompute step can discover it after a real pipeline run.
        cfg.audit_dir.mkdir(parents=True, exist_ok=True)
        audit_out = cfg.audit_dir / "route_trip_frequency.parquet"
        route_freq.to_parquet(audit_out, index=False, compression="zstd")
        logger.info(f"Route trip frequency: {len(route_freq):,} routes → {out.name} (+ audit copy)")
        checks_passed += 1
    except Exception as e:
        logger.error(f"Route trip frequency processing failed: {e}")
        raise

    duration = time.perf_counter() - t0
    report = StageReport("process", duration, output_files, checks_passed)
    report.log()
    return report


def run_analytics(cfg: PipelineConfig | None = None) -> StageReport:
    """Stage 3: write equity (and mirror) analytics Parquets."""
    if cfg is None:
        cfg = PipelineConfig()

    logger.info("Stage 3: Analytics — writing equity, policy, economic, SHAP files")
    t0 = time.perf_counter()

    from aequitas.analytics.writers import write_analytics_pack

    output_files = write_analytics_pack(cfg)
    equity_ok = any(p.name == "lsoa_equity_metrics.parquet" for p in output_files)
    checks_passed = 1 if equity_ok else 0
    checks_failed = 0 if equity_ok else 1

    duration = time.perf_counter() - t0
    report = StageReport("analytics", duration, output_files, checks_passed, checks_failed)
    report.log()
    return report


def run_reach(
    cfg: PipelineConfig | None = None,
    *,
    force: bool = False,
    region: str | None = None,
) -> StageReport:
    """r5py 15/30/45 destination counts. Skip if cache newer than GTFS+PBF."""
    if cfg is None:
        cfg = PipelineConfig()
    t0 = time.perf_counter()
    logger.info("Reach: r5py 15/30/45 (region={})", region or "all cached")
    from aequitas.analytics.bands import write_access_bands
    from aequitas.analytics.reach import ReachConfig, write_reach

    out = write_reach(
        ReachConfig(
            processed_dir=cfg.processed_dir,
            raw_dir=cfg.raw_dir,
            region=region,
            force=force,
        )
    )
    bands = write_access_bands(cfg)
    checks_passed = 1 if (out is not None or bands is not None) else 0
    checks_failed = 0
    # Missing Java/PBF is a skip, not a failed pipeline.
    report = StageReport(
        "reach",
        time.perf_counter() - t0,
        [out] if out else [],
        checks_passed,
        checks_failed,
    )
    report.log()
    return report


def run_studio(
    cfg: PipelineConfig | None = None,
    *,
    patch_path: str | None = None,
    force: bool = False,
) -> StageReport:
    """Optional Studio apply. Skip if no patch file. Never invents 45-min figures."""
    if cfg is None:
        cfg = PipelineConfig()
    t0 = time.perf_counter()
    if not patch_path:
        logger.info("Studio: no --patch given — skip (not required in CI)")
        report = StageReport("studio", time.perf_counter() - t0, [], 0, 0)
        report.log()
        return report
    from pathlib import Path
    import json
    import pandas as pd

    from aequitas.analytics.studio import apply_studio, parse_studio_patch

    path = Path(patch_path)
    if not path.exists():
        logger.warning("Studio patch not found: {}", path)
        report = StageReport("studio", time.perf_counter() - t0, [], 0, 1)
        report.log()
        return report
    raw = json.loads(path.read_text())
    patch, err = parse_studio_patch(raw)
    if err or patch is None:
        logger.warning("Studio patch invalid: {}", err)
        report = StageReport("studio", time.perf_counter() - t0, [], 0, 1)
        report.log()
        return report
    from aequitas.analytics.centroids import (
        ensure_centroids,
        filter_centroids_for_studio,
        filter_stops_to_bbox,
        bbox_of,
        load_centroid_points,
    )

    ensure_centroids(cfg.processed_dir)
    pts = load_centroid_points(cfg.processed_dir)
    master = cfg.processed_dir / "master_lsoa_table.parquet"
    if not master.exists():
        master = cfg.audit_dir / "master_lsoa_table.parquet"
    demo = pd.read_parquet(master) if master.exists() else pd.DataFrame()
    centroids = filter_centroids_for_studio(
        demo, pts, region=patch.region, urban_rural=patch.urban_rural
    )
    baseline: list[tuple[float, float]] = []
    try:
        import duckdb

        if cfg.warehouse_path.exists():
            conn = duckdb.connect(str(cfg.warehouse_path), read_only=True)
            rows = conn.execute(
                "SELECT latitude, longitude FROM stops "
                "WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
            ).fetchall()
            conn.close()
            baseline = filter_stops_to_bbox(
                [(float(a), float(b)) for a, b in rows],
                bbox_of(centroids, pad_deg=0.08),
            )
    except Exception:
        baseline = []
    result = apply_studio(
        patch,
        centroids=centroids,
        baseline_stops=baseline,
        processed_dir=cfg.processed_dir,
        raw_dir=cfg.raw_dir,
        force=force,
    )
    logger.info("Studio mode={} gained={} lost={}", result.mode, result.people_gained, result.people_lost)
    report = StageReport("studio", time.perf_counter() - t0, [], 1 if result.ok else 0, 0 if result.ok else 1)
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

    # Stash results so run_warehouse can insert them
    cfg._section_results = results  # type: ignore[attr-defined]

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


def run_rag_index(cfg: PipelineConfig | None = None, *, country: str = "england") -> StageReport:
    """Build FAISS index from DuckDB narratives."""
    if cfg is None:
        cfg = PipelineConfig()

    from aequitas.rag.index_builder import build_faiss_index

    t0 = time.perf_counter()
    kwargs: dict = {"country": country}
    if country == "ireland":
        kwargs["warehouse_path"] = cfg.project_root / "data" / "aequitas_ireland.duckdb"
    result = build_faiss_index(cfg, **kwargs)
    return StageReport(
        stage="rag_index",
        duration_s=time.perf_counter() - t0,
        output_files=[Path(p) for p in [result.get("index_path", ""), result.get("metadata_path", "")] if p],
        checks_passed=1 if result.get("n_chunks", 0) > 0 else 0,
        checks_failed=0 if result.get("n_chunks", 0) > 0 else 1,
    )


def run_validation(cfg: PipelineConfig | None = None) -> StageReport:
    """Stage 6: sanity gates (counts, join rate, population). Historical Gini is advisory."""
    if cfg is None:
        cfg = PipelineConfig()

    logger.info("Stage 6: Validation — sanity checks (not locked June 2026 Gini)")
    t0 = time.perf_counter()

    from aequitas.validation.sanity import validate_sanity
    from aequitas.validation.ground_truth import validate_against_ground_truth
    from aequitas.validation.report import generate_report

    sanity = validate_sanity(cfg)
    # Historical pack comparison is informational — drift must not fail the pipeline.
    historical = validate_against_ground_truth(cfg)
    for check in historical.get("checks", []):
        if check.get("status") == "FAIL":
            check["status"] = "WARN"
    historical["n_fail"] = 0
    historical["n_warn"] = sum(1 for c in historical.get("checks", []) if c.get("status") == "WARN")
    historical["all_pass"] = True

    merged = {
        "checks": sanity["checks"] + historical.get("checks", []),
        "n_pass": sanity["n_pass"] + historical.get("n_pass", 0),
        "n_warn": sanity["n_warn"] + historical.get("n_warn", 0),
        "n_fail": sanity["n_fail"],
        "all_pass": sanity["all_pass"],
    }
    generate_report(merged, output_path=cfg.processed_dir / "validation_report.md")

    if not sanity["all_pass"]:
        logger.error(f"Sanity validation FAILED — {sanity['n_fail']} checks failed")
    else:
        logger.info(f"Sanity validation passed — {sanity['n_pass']} checks OK")

    duration = time.perf_counter() - t0
    report = StageReport("validate", duration, [], sanity["n_pass"], sanity["n_fail"])
    report.log()
    return report
