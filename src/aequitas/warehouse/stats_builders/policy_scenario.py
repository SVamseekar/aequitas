"""Stats builder for policy_scenario.j2 and scenario_comparison.j2.

Covers: ps1_freq_restoration, ps2_evening_extension, ps3_drt_rural,
ps4_franchise, g5_scenario_model (single-scenario shape), and
ps5_scenario_comparison (portfolio shape, different template).

policy_scenarios.parquet has exactly 4 rows (A-D) mapped 1:1 by row order and
provides the England-wide constants for name/scope/cost/co2/confidence
(unchanged by B2). `population_affected` and `annual_additional_trips` are
recomputed per region/urban_rural filter by re-deriving each scenario's LSOA
(or LAD) scope from `lsoa_policy_synthesis` (+ `master_lsoa_table.elderly_pct`
for ps3) and `lta_franchising_readiness` (for ps4), per
docs/superpowers/plans/2026-06-11-warehouse-staleness-and-filter-bugs.md (B2).

Scope filters (must reproduce the national constants in policy_scenarios.parquet
for the "all"/"all" combo — see tests):
- ps1: imd_decile == 1 (bottom/most-deprived decile) -> 3,375 LSOAs, pop 5,689,818
- ps2: evening_isolated == True -> 5,189 LSOAs, pop 8,392,662
- ps3: urban_rural contains "Rural" AND elderly_pct > 24.7 (national Q3, frozen
  — see figures-registry ST-037) -> 3,192 LSOAs, pop 5,243,877
- ps4: top-5 LADs by franchising_readiness (LAD-grain, not region-decomposable)
  -> 5 LADs, pop 760,008. Kept as the England-wide constant for all filters.

NaN coalescing to 0.0 is required: co2_saving_t_yr is NaN for rows B/C/D,
estimated_annual_cost_m is NaN for row D — the Jinja templates call
|round(1) and |int on these fields, which raise on None/NaN.
"""

import math

import pandas as pd

_ROW_BY_SECTION: dict[str, int] = {
    "ps1_freq_restoration": 0,
    "ps2_evening_extension": 1,
    "ps3_drt_rural": 2,
    "ps4_franchise": 3,
    "g5_scenario_model": 0,  # flagship scenario headlines the overview slot
}

_SCENARIO_FIELDS = (
    "name", "scope", "population_affected", "annual_additional_trips",
    "estimated_annual_cost_m", "co2_saving_t_yr", "confidence",
)

# National Q3 (75th percentile) of elderly_pct over all 33,755 LSOAs, frozen
# at build time so per-region/urban_rural re-filters use the same threshold
# as the national scope (see figures-registry ST-037). Recomputing this
# quantile on a filtered subset would change the scope definition.
ELDERLY_PCT_Q75_THRESHOLD = 24.7


def _coalesce(value: float) -> float:
    return 0.0 if value is None or (isinstance(value, float) and math.isnan(value)) else float(value)


def _row_to_scenario(row: pd.Series) -> dict:
    scenario = {field: row[field] for field in _SCENARIO_FIELDS}
    scenario["estimated_annual_cost_m"] = _coalesce(scenario["estimated_annual_cost_m"])
    scenario["co2_saving_t_yr"] = _coalesce(scenario["co2_saving_t_yr"])
    scenario["population_affected"] = int(scenario["population_affected"])
    scenario["annual_additional_trips"] = int(scenario["annual_additional_trips"])
    scenario["name"] = str(scenario["name"])
    scenario["scope"] = str(scenario["scope"])
    scenario["confidence"] = str(scenario["confidence"])
    return scenario


def _scope_population(scope_df: pd.DataFrame) -> int:
    """Sum `population` over a scope-filtered LSOA frame (0 if empty/missing)."""
    if scope_df.empty or "population" not in scope_df.columns:
        return 0
    return int(scope_df["population"].sum())


def _ps1_scope(elderly_df: pd.DataFrame) -> pd.DataFrame:
    """Bottom (most-deprived) IMD decile — imd_decile == 1."""
    return elderly_df[elderly_df["imd_decile"] == 1]


def _ps2_scope(elderly_df: pd.DataFrame) -> pd.DataFrame:
    """Evening-isolated LSOAs."""
    return elderly_df[elderly_df["evening_isolated"] == True]  # noqa: E712


def _ps3_scope(elderly_df: pd.DataFrame) -> pd.DataFrame:
    """Rural LSOAs with elderly_pct above the frozen national Q3 threshold."""
    if "elderly_pct" not in elderly_df.columns:
        return elderly_df.iloc[0:0]
    is_rural = elderly_df["urban_rural"].str.contains("Rural", na=False)
    is_elderly = elderly_df["elderly_pct"] > ELDERLY_PCT_Q75_THRESHOLD
    return elderly_df[is_rural & is_elderly]


def _recompute_population_affected(
    row_index: int, elderly_df: pd.DataFrame, national_population: int,
) -> int | None:
    """Recompute population_affected for ps1-ps3 from the filtered LSOA frame.

    Args:
        row_index: 0/1/2 for ps1/ps2/ps3 (ps4 is LAD-level, returns None).
        elderly_df: Region/urban_rural-filtered lsoa_policy_synthesis rows,
            with elderly_pct merged on for ps3.
        national_population: National population_affected constant for this
            scenario (used as a fallback if the scope frame is empty/missing
            required columns).

    Returns:
        Recomputed population sum, or None for ps4 (LAD-level, unchanged).
    """
    if elderly_df.empty:
        return national_population

    if row_index == 0 and "imd_decile" in elderly_df.columns:
        return _scope_population(_ps1_scope(elderly_df))
    if row_index == 1 and "evening_isolated" in elderly_df.columns:
        return _scope_population(_ps2_scope(elderly_df))
    if row_index == 2 and {"urban_rural", "elderly_pct"}.issubset(elderly_df.columns):
        return _scope_population(_ps3_scope(elderly_df))
    if row_index == 3:
        return None

    return national_population


def _scale_trips(annual_additional_trips: int, population_affected: int, national_population: int) -> int:
    """Scale annual_additional_trips proportionally to the recomputed population.

    No per-LSOA trip-gap/SQI breakdown is carried into this builder, so the
    national annual_additional_trips constant is scaled by the ratio of
    recomputed to national population_affected. For "all"/"all" this is a
    no-op (ratio == 1).
    """
    if national_population <= 0:
        return annual_additional_trips
    ratio = population_affected / national_population
    return int(round(annual_additional_trips * ratio))


def _build_single(
    scenarios_df: pd.DataFrame, row_index: int, elderly_df: pd.DataFrame,
) -> dict:
    if scenarios_df.empty or row_index >= len(scenarios_df):
        return {}

    scenario = _row_to_scenario(scenarios_df.iloc[row_index])
    national_population = scenario["population_affected"]
    national_trips = scenario["annual_additional_trips"]

    recomputed = _recompute_population_affected(row_index, elderly_df, national_population)
    if recomputed is not None:
        scenario["population_affected"] = recomputed
        scenario["annual_additional_trips"] = _scale_trips(national_trips, recomputed, national_population)

    return {"scenario": scenario}


def _build_comparison(scenarios_df: pd.DataFrame, elderly_df: pd.DataFrame) -> dict:
    if scenarios_df.empty:
        return {}

    scenarios = []
    best_name: str | None = None
    best_ratio = math.inf

    for row_index, (_, row) in enumerate(scenarios_df.iterrows()):
        cost_m = _coalesce(row["estimated_annual_cost_m"])
        national_population = int(row["population_affected"])

        recomputed = _recompute_population_affected(row_index, elderly_df, national_population)
        population = national_population if recomputed is None else recomputed

        scenarios.append({
            "name": str(row["name"]),
            "population": population,
            "cost_m": cost_m,
            "co2_t": _coalesce(row["co2_saving_t_yr"]),
        })
        if cost_m > 0 and population > 0:
            ratio = (cost_m * 1e6) / population
            if ratio < best_ratio:
                best_ratio = ratio
                best_name = str(row["name"])

    return {"scenarios": scenarios, "best_bcr_scenario": best_name}


def build_policy_scenario_stats(
    section_id: str,
    scenarios_df: pd.DataFrame,
    elderly_df: pd.DataFrame | None = None,
) -> dict:
    """Build stats for ps1-ps4, g5_scenario_model, or ps5_scenario_comparison.

    Args:
        section_id: One of the 6 covered section IDs.
        scenarios_df: The full 4-row policy_scenarios.parquet, providing
            name/scope/cost/co2/confidence constants (unchanged by B2).
        elderly_df: Region/urban_rural-filtered lsoa_policy_synthesis rows
            (with `elderly_pct` merged on from master_lsoa_table), used to
            recompute population_affected/annual_additional_trips for
            ps1-ps3 per the scope filters in this module's docstring. ps4
            (LAD-level) is unaffected and stays at its national constant.
            If None or empty, falls back to the national constants.

    Returns:
        For ps1-ps4/g5: `{"scenario": {...}}` matching policy_scenario.j2.
        For ps5: `{"scenarios": [...], "best_bcr_scenario": ...}` matching
        scenario_comparison.j2. `{}` if scenarios_df is empty.
    """
    if elderly_df is None:
        elderly_df = pd.DataFrame()

    if section_id == "ps5_scenario_comparison":
        return _build_comparison(scenarios_df, elderly_df)

    row_index = _ROW_BY_SECTION.get(section_id)
    if row_index is None:
        return {}
    return _build_single(scenarios_df, row_index, elderly_df)
