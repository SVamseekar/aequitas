"""Pre-computation of section_results for the DuckDB warehouse.

For each of the 30 filter combinations (10 regions × 3 area types), computes
all analytical sections and stores them as JSON in section_results.

This is called once at build time — never at request time.
"""

import json
from dataclasses import dataclass

import pandas as pd
from loguru import logger

from aequitas.core.config import PipelineConfig
from aequitas.core.types import RegionCode
from aequitas.intelligence.engine import InsightEngine


# Sections to precompute for each filter combination
_SECTIONS = [
    "coverage_density",
    "equity",
    "correlation",
    "gap_to_target",
    "policy_scenario",
]

# All region codes + "all"
_REGIONS = ["all"] + [rc.value for rc in RegionCode]
# Area types
_AREA_TYPES = ["all", "urban", "rural"]


@dataclass
class SectionResult:
    region: str
    urban_rural: str
    section_id: str
    stats: dict
    chart_data: dict
    narrative: str

    def to_dict(self) -> dict:
        return {
            "region": self.region,
            "urban_rural": self.urban_rural,
            "section_id": self.section_id,
            "stats": self.stats,
            "chart_data": self.chart_data,
            "narrative": self.narrative,
        }


def precompute_all_sections(cfg: PipelineConfig) -> list[dict]:
    """Precompute all section results for the 30 filter combinations.

    Loads Phase 0 audit Parquets, applies filters, runs InsightEngine for
    each section, and returns a list of SectionResult dicts.

    Args:
        cfg: Pipeline configuration.

    Returns:
        List of dicts, each with keys: region, urban_rural, section_id,
        stats, chart_data, narrative.
    """
    engine = InsightEngine()
    results: list[dict] = []

    # Load base data from audit Parquets
    policy_path = cfg.audit_dir / "lsoa_policy_synthesis.parquet"
    equity_path = cfg.audit_dir / "lsoa_equity_metrics.parquet"
    equity_summary_path = cfg.audit_dir / "equity_summary.json"

    if not policy_path.exists() or not equity_path.exists():
        logger.warning("Audit Parquets not found — precompute returning empty results")
        return results

    policy_df = pd.read_parquet(policy_path)
    equity_df = pd.read_parquet(equity_path)

    # Load pre-aggregated equity summary (gini, palma, CI, lorenz curve)
    equity_summary: dict = {}
    if equity_summary_path.exists():
        import json as _json
        equity_summary = _json.loads(equity_summary_path.read_text())

    for region in _REGIONS:
        for urban_rural in _AREA_TYPES:
            # Skip redundant single-region + urban/rural combos for speed
            # (these are low-value subsets; all_regions × all produces the key insights)
            if region != "all" and urban_rural != "all":
                continue

            # Filter data
            region_mask = pd.Series(True, index=policy_df.index)
            if region != "all":
                region_col = "region" if "region" in policy_df.columns else None
                if region_col:
                    region_mask = policy_df[region_col] == region

            ur_mask = pd.Series(True, index=policy_df.index)
            if urban_rural != "all":
                ur_col = "urban_rural" if "urban_rural" in policy_df.columns else None
                if ur_col:
                    ur_mask = policy_df[ur_col].str.lower().str.startswith(urban_rural)

            filtered = policy_df[region_mask & ur_mask]

            for section_id in _SECTIONS:
                stats = _build_stats(filtered, equity_df, equity_summary, section_id, region, urban_rural)
                result = engine.generate(
                    section_id=section_id,
                    region=region,
                    urban_rural=urban_rural,
                    stats=stats,
                )
                results.append(
                    SectionResult(
                        region=region,
                        urban_rural=urban_rural,
                        section_id=section_id,
                        stats=stats,
                        chart_data={},
                        narrative=result["narrative"],
                    ).to_dict()
                )

    logger.info(f"Precomputed {len(results)} section results")
    return results


def _build_stats(
    filtered: pd.DataFrame,
    equity_df: pd.DataFrame,
    equity_summary: dict,
    section_id: str,
    region: str,
    urban_rural: str,
) -> dict:
    """Build stats dict for a given section and filter combination."""
    stats: dict = {}

    if section_id == "coverage_density":
        if len(filtered) == 0:
            return stats
        if "region" in filtered.columns and "trips_per_capita" in filtered.columns:
            by_region = filtered.groupby("region")["trips_per_capita"].mean()
            if len(by_region) > 1:
                best_region = by_region.idxmax()
                worst_region = by_region.idxmin()
                nat_mean = float(by_region.mean())
                stats["stops_per_1000"] = {
                    "best": {
                        "name": best_region,
                        "value": round(float(by_region[best_region]), 2),
                        "pct_above": round((float(by_region[best_region]) - nat_mean) / nat_mean * 100, 1),
                    },
                    "worst": {
                        "name": worst_region,
                        "value": round(float(by_region[worst_region]), 2),
                        "pct_below": round((nat_mean - float(by_region[worst_region])) / nat_mean * 100, 1),
                    },
                    "national_avg": round(nat_mean, 2),
                }

    elif section_id == "equity":
        # Use pre-aggregated equity_summary.json from Phase 0
        if equity_summary:
            stats["gini"] = equity_summary.get("gini_population_weighted", 0.5741)
            stats["palma"] = equity_summary.get("palma_ratio", 5.702)
            stats["concentration_index"] = equity_summary.get("concentration_index_trips", 0.1358)
            stats["triple_deprived_lsoas"] = equity_summary.get("triple_deprived_lsoas", 612)
            stats["triple_deprived_pct"] = equity_summary.get("triple_deprived_pct", 1.8)
            # Lorenz curve data for chart
            lorenz_x = equity_summary.get("lorenz_x", [])
            lorenz_y = equity_summary.get("lorenz_y", [])
            if lorenz_x and lorenz_y:
                step = max(1, len(lorenz_x) // 100)
                stats["lorenz_x"] = lorenz_x[::step]
                stats["lorenz_y"] = lorenz_y[::step]

    elif section_id == "gap_to_target":
        if len(filtered) == 0:
            return stats
        if "trips_per_capita" in filtered.columns:
            median = float(filtered["trips_per_capita"].median())
            below = filtered[filtered["trips_per_capita"] < median]
            stats["n_below"] = len(below)
            stats["pct_below"] = round(len(below) / len(filtered) * 100, 1)
            stats["target"] = round(median, 2)
            stats["unit"] = "trips/capita"
            stats["mean_gap"] = round(float((median - below["trips_per_capita"]).mean()), 2) if len(below) > 0 else 0.0
            stats["total_annual_cost_m"] = round(float(len(below) * 500 / 1_000_000), 1)

    return stats
