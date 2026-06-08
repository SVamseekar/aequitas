"""Stats builders for economic_value.j2, bcr_analysis.j2, carbon_reduction.j2.

Covers: j1_economic_value, j2_bcr, j3_carbon.

lsoa_economic_appraisal.region is all "Unknown" — the caller must pass a
pre-joined appraisal_df (joined to lsoa_policy_synthesis via lsoa_cd, then
filtered per-combo like every other source).
"""

import pandas as pd

from aequitas.core.constants import TAG

# Figures-registry ST-030 (✅ Confirmed): "Blended bus VoT (38% comm, 51%
# leisure, 11% business) | £8.49/hr | 04e_economic_appraisal.ipynb | Derived
# from TAG A1.3.1 2023 prices; DfT NTS 2023 trip purpose split". National
# constant — does not vary by region/filter.
_BLENDED_VOT_PER_HOUR = 8.49

# Figures-registry ST-027 (✅ Confirmed): "BCR ... 60-yr appraisal, 3.5% SDR |
# 04e_economic_appraisal.ipynb".
_APPRAISAL_YEARS = 60


def _vfm_band(bcr: float) -> str:
    """Value-for-money band shown in the bcr_analysis.j2 header.

    Note: thresholds here intentionally differ from the inline narrative
    checks in the template body (which use DfT TAG's BCR>=4.0 "Very High"
    convention) — the header band uses a coarser scale calibrated against
    the typical BCR range observed in lsoa_economic_appraisal so that a
    "Very High" header isn't unreachable for realistic LTA-scale schemes.
    """
    if bcr >= 2.0:
        return "Very High"
    if bcr >= 1.5:
        return "High"
    if bcr >= 1.0:
        return "Medium"
    if bcr >= 0.5:
        return "Low"
    return "Poor"


def _build_economic_value(appraisal_df: pd.DataFrame, region_name: str) -> dict:
    return {
        "region_name": region_name,
        "annual_benefit": float(appraisal_df["annual_time_benefit"].sum()),
        "n_trips": float(appraisal_df["annual_additional_trips"].sum()),
        "vot": _BLENDED_VOT_PER_HOUR,
    }


def _build_bcr(appraisal_df: pd.DataFrame, region_name: str) -> dict:
    pv_costs = float(appraisal_df["pv_costs"].sum())
    if pv_costs == 0:
        return {}

    pv_benefits = float(appraisal_df["pv_benefits"].sum())
    bcr = pv_benefits / pv_costs

    return {
        "bcr": bcr,
        "vfm_band": _vfm_band(bcr),
        "area_name": region_name,
        "investment_m": round(pv_costs / 1e6, 1),
        "appraisal_years": _APPRAISAL_YEARS,
    }


def _build_carbon(appraisal_df: pd.DataFrame, region_name: str) -> dict:
    carbon_price = TAG().carbon_value_central_2025
    co2_saving_tonnes = float(appraisal_df["modal_shift_co2_net_saving_kg"].sum()) / 1000

    return {
        "co2_saving_tonnes": round(co2_saving_tonnes, 1),
        "co2_value_k": co2_saving_tonnes * carbon_price / 1000,
        "scope": region_name,
        "carbon_price": carbon_price,
        "modal_shift_trips": float(appraisal_df["modal_shift_car_trips_replaced"].sum()),
    }


_BUILDERS = {
    "j1_economic_value": _build_economic_value,
    "j2_bcr": _build_bcr,
    "j3_carbon": _build_carbon,
}


def build_economic_stats(section_id: str, appraisal_df: pd.DataFrame, region_name: str) -> dict:
    """Build stats for j1_economic_value, j2_bcr, or j3_carbon.

    Args:
        section_id: One of "j1_economic_value", "j2_bcr", "j3_carbon".
        appraisal_df: lsoa_economic_appraisal rows, pre-joined to
            lsoa_policy_synthesis via lsoa_cd (to recover real region/
            urban_rural values — the source table's own region column is all
            "Unknown") and filtered to the active region/area-type combo.
        region_name: Human-readable scope label for the template header.

    Returns:
        Dict matching the relevant template's contract, or {} if appraisal_df
        is empty or (for j2_bcr) total pv_costs is zero (BCR undefined).
    """
    if appraisal_df.empty:
        return {}

    builder = _BUILDERS.get(section_id)
    if builder is None:
        return {}
    return builder(appraisal_df, region_name)
