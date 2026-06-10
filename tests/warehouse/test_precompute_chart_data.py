"""Integration tests for chart_dispatch wired into precompute_all_sections."""

import math

import pandas as pd
import pytest

from aequitas.core.config import PipelineConfig
from aequitas.warehouse.chart_dispatch import build_chart_data
from aequitas.warehouse.precompute import REGION_NAMES, _dispatch, _load_sources, _Sources


@pytest.fixture(scope="module")
def cfg() -> PipelineConfig:
    return PipelineConfig()


@pytest.fixture(scope="module")
def sources(cfg: PipelineConfig) -> _Sources:
    src = _load_sources(cfg)
    assert src is not None
    return src


def _build_for(
    section_id: str, region: str, urban_rural: str, sources: _Sources
) -> tuple[dict, dict]:
    policy_df = sources.policy_df
    region_name = "England" if region == "all" else REGION_NAMES[region]
    region_value = "all" if region == "all" else region_name
    region_mask = pd.Series(True, index=policy_df.index)
    if region_value != "all":
        region_mask = policy_df["region"] == region_value

    ur_mask = pd.Series(True, index=policy_df.index)
    if urban_rural != "all":
        ur_mask = policy_df["urban_rural"].str.lower().str.startswith(urban_rural)

    filtered = policy_df[region_mask & ur_mask]
    region_df = policy_df[region_mask]
    lsoa_cds = filtered["lsoa_cd"]

    stats = _dispatch(
        section_id=section_id,
        region=region,
        urban_rural=urban_rural,
        region_name=region_name,
        filtered=filtered,
        region_df=region_df,
        sources=sources,
        lsoa_cds=lsoa_cds,
    )
    chart_data = build_chart_data(
        section_id=section_id,
        stats=stats,
        region=region,
        region_name=region_name,
        urban_rural=urban_rural,
        filtered=filtered,
        region_df=region_df,
        sources=sources,
        lsoa_cds=lsoa_cds,
    )
    return stats, chart_data


def test_f1_gini_chart_matches_stats(sources: _Sources) -> None:
    """The f1_gini section's lorenz_curve chart gini value matches the computed stats."""
    stats, chart_data = _build_for("f1_gini", "all", "all", sources)
    assert chart_data
    assert chart_data["type"] == "lorenz_curve"
    assert math.isclose(chart_data["gini"], stats["gini"], abs_tol=1e-3)


def test_a1_route_density_chart_is_horizontal_bar(sources: _Sources) -> None:
    """The a1_route_density section produces a horizontal_bar chart."""
    _, chart_data = _build_for("a1_route_density", "all", "all", sources)
    assert chart_data
    assert chart_data["type"] == "horizontal_bar"


def test_chart_type_variety_across_sample(sources: _Sources) -> None:
    """At least 6 distinct chart types appear across a sample of sections/regions."""
    from aequitas.intelligence.section_registry import SECTION_REGISTRY

    types_seen: set[str] = set()
    for section_id in SECTION_REGISTRY:
        for region in ("all", "E12000001"):
            _, chart_data = _build_for(section_id, region, "all", sources)
            if chart_data:
                types_seen.add(chart_data["type"])

    assert len(types_seen) >= 6, f"Only {len(types_seen)} chart types: {types_seen}"
