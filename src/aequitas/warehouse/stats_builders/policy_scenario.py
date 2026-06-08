"""Stats builder for policy_scenario.j2 and scenario_comparison.j2.

Covers: ps1_freq_restoration, ps2_evening_extension, ps3_drt_rural,
ps4_franchise, g5_scenario_model (single-scenario shape), and
ps5_scenario_comparison (portfolio shape, different template).

policy_scenarios.parquet has exactly 4 rows (A-D) mapped 1:1 by row order.
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


def _coalesce(value: float) -> float:
    return 0.0 if value is None or (isinstance(value, float) and math.isnan(value)) else float(value)


def _row_to_scenario(row: pd.Series) -> dict:
    scenario = {field: row[field] for field in _SCENARIO_FIELDS}
    scenario["estimated_annual_cost_m"] = _coalesce(scenario["estimated_annual_cost_m"])
    scenario["co2_saving_t_yr"] = _coalesce(scenario["co2_saving_t_yr"])
    scenario["population_affected"] = int(scenario["population_affected"])
    return scenario


def _build_single(scenarios_df: pd.DataFrame, row_index: int) -> dict:
    if scenarios_df.empty or row_index >= len(scenarios_df):
        return {}
    return {"scenario": _row_to_scenario(scenarios_df.iloc[row_index])}


def _build_comparison(scenarios_df: pd.DataFrame) -> dict:
    if scenarios_df.empty:
        return {}

    scenarios = []
    best_name: str | None = None
    best_ratio = math.inf

    for _, row in scenarios_df.iterrows():
        cost_m = _coalesce(row["estimated_annual_cost_m"])
        population = int(row["population_affected"])
        scenarios.append({
            "name": row["name"],
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


def build_policy_scenario_stats(section_id: str, scenarios_df: pd.DataFrame) -> dict:
    """Build stats for ps1-ps4, g5_scenario_model, or ps5_scenario_comparison.

    Args:
        section_id: One of the 6 covered section IDs.
        scenarios_df: The full 4-row policy_scenarios.parquet (not filtered —
            scenarios are England-wide interventions, not region-scoped).

    Returns:
        For ps1-ps4/g5: `{"scenario": {...}}` matching policy_scenario.j2.
        For ps5: `{"scenarios": [...], "best_bcr_scenario": ...}` matching
        scenario_comparison.j2. `{}` if scenarios_df is empty.
    """
    if section_id == "ps5_scenario_comparison":
        return _build_comparison(scenarios_df)

    row_index = _ROW_BY_SECTION.get(section_id)
    if row_index is None:
        return {}
    return _build_single(scenarios_df, row_index)
