"""InsightEngine context resolver — determines analysis scope and groups.

Three scopes:
- ALL_REGIONS: all 9 ONS regions, enables rankings + comparisons
- SINGLE_REGION: one specific region, compare to national average
- SUBSET: filtered by urban/rural (or other criterion), descriptive only
"""

from dataclasses import dataclass
from enum import Enum

from aequitas.core.types import RegionCode


class AnalysisScope(Enum):
    ALL_REGIONS = "all_regions"
    SINGLE_REGION = "single_region"
    SUBSET = "subset"


@dataclass(frozen=True)
class AnalysisContext:
    """Resolved context for an InsightEngine analysis run.

    Attributes:
        scope: One of ALL_REGIONS, SINGLE_REGION, SUBSET.
        region: Region code filter ("all" or ONS region code E12xxxxxx).
        urban_rural: Area type filter ("all", "urban", or "rural").
        n_groups: Number of comparison groups (9 for all_regions, 1 otherwise).
        show_rankings: True only when scope is ALL_REGIONS.
        compare_to_national: True when scope is SINGLE_REGION.
    """

    scope: AnalysisScope
    region: str
    urban_rural: str
    n_groups: int
    show_rankings: bool
    compare_to_national: bool


def resolve_context(region: str = "all", urban_rural: str = "all") -> AnalysisContext:
    """Resolve analysis scope from filter parameters.

    Args:
        region: ONS region code (e.g. "E12000003") or "all".
        urban_rural: "all", "urban", or "rural".

    Returns:
        AnalysisContext with scope, group count, and display flags.

    Raises:
        ValueError: If region code format is invalid (not "all" or E12xxxxxx).
    """
    if region != "all" and not (region.startswith("E12") and len(region) == 9):
        raise ValueError(
            f"Invalid region code '{region}'. Must be 'all' or ONS code E12xxxxxx."
        )
    if urban_rural not in {"all", "urban", "rural"}:
        raise ValueError(f"Invalid urban_rural '{urban_rural}'. Must be all/urban/rural.")

    if region == "all" and urban_rural == "all":
        return AnalysisContext(
            scope=AnalysisScope.ALL_REGIONS,
            region=region,
            urban_rural=urban_rural,
            n_groups=9,
            show_rankings=True,
            compare_to_national=False,
        )

    if region != "all" and urban_rural == "all":
        return AnalysisContext(
            scope=AnalysisScope.SINGLE_REGION,
            region=region,
            urban_rural=urban_rural,
            n_groups=1,
            show_rankings=False,
            compare_to_national=True,
        )

    # Subset: any combination with urban_rural filter (including single region + area type)
    return AnalysisContext(
        scope=AnalysisScope.SUBSET,
        region=region,
        urban_rural=urban_rural,
        n_groups=1,
        show_rankings=False,
        compare_to_national=False,
    )
