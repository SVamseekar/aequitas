"""Validation gates — sanity checks on entity counts, match rates, and analytics.

Gates come from the data-quality.md rules and Phase 0 ground truth.
All gates return True (pass) or False (fail).
"""

from aequitas.core.constants import LSOA_COUNT_ENGLAND, POPULATION_ENGLAND

# Ground truth entity counts from Phase 0 (locked 2026-03-11)
_GT_STOPS = 274_719
_GT_ROUTES = 13_099  # Phase 0 snapshot; BODS is live, allow ±10%
_GT_TRIPS = 1_752_443
_GT_LSOAS_ZERO_STOPS = 4_245

# Tolerances
_POPULATION_TOL = 100
_ROUTES_DRIFT_PCT = 0.10  # BODS is a live feed — allow 10% drift


def check_population_total(population: int) -> bool:
    """Validate England population total against ONS Census 2021.

    Args:
        population: Computed total population sum across all LSOAs.

    Returns:
        True if within ±100 of 56,490,056.
    """
    return abs(population - POPULATION_ENGLAND) <= _POPULATION_TOL


def check_lsoa_count(count: int) -> bool:
    """Validate England LSOA count = 33,755.

    Args:
        count: Number of LSOAs in the processed dataset.

    Returns:
        True if count == 33,755 (exact).
    """
    return count == LSOA_COUNT_ENGLAND


def check_entity_counts(stops: int, routes: int) -> bool:
    """Sanity check stop and route counts against ground truth.

    Stops must be exactly 274,719 (NaPTAN is filtered deterministically).
    Routes allow ±10% because BODS is a live feed.

    Args:
        stops: Number of England active bus stops after filtering.
        routes: Number of unique BODS routes.

    Returns:
        True if both are within acceptable bounds.
    """
    stops_ok = stops == _GT_STOPS
    routes_ok = abs(routes - _GT_ROUTES) / _GT_ROUTES <= _ROUTES_DRIFT_PCT
    return stops_ok and routes_ok


def check_match_rates(stop_lsoa_rate: float, demographic_rates: list[float] | None = None) -> bool:
    """Validate spatial join and demographic merge match rates.

    Args:
        stop_lsoa_rate: Fraction of stops matched to an LSOA (e.g. 0.9999).
        demographic_rates: Optional list of demographic merge rates (all must be ≥ 0.95).

    Returns:
        True if all rates meet thresholds.
    """
    if stop_lsoa_rate < 0.9990:
        return False
    if demographic_rates is not None:
        if any(r < 0.95 for r in demographic_rates):
            return False
    return True
