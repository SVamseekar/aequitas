"""TAG v2.03fc and DESNZ 2025 constants — single source of truth.

Values loaded from data/audit/*.json (extracted in Phase 0 notebooks 03f, 03g).
Do NOT hardcode appraisal values inline anywhere else in the codebase.
"""

import json
from dataclasses import dataclass
from functools import cache as _cache
from pathlib import Path

_AUDIT_DIR = Path(__file__).parent.parent.parent.parent / "data" / "audit"

# Ground truth denominators — do not change without re-running audit
POPULATION_ENGLAND: int = 56_490_056
LSOA_COUNT_ENGLAND: int = 33_755


@dataclass(frozen=True)
class TAGConstants:
    """TAG Databook v2.03fc values (Dec 2025)."""

    # Value of Time — Source VoT sheet, 2014 prices (per hour)
    vot_commuting_2014: float
    vot_leisure_2014: float
    vot_business_avg_2014: float
    # A1.3.1 published, 2023 prices (factor cost, per hour)
    vot_commuting_2023: float
    vot_leisure_2023: float
    vot_business_avg_2023: float
    # Carbon appraisal, 2020 prices (£/tonne CO2e)
    carbon_value_central_2010: float
    carbon_value_central_2025: float
    carbon_value_central_2030: float
    # Discount rate
    social_discount_rate: float


@dataclass(frozen=True)
class DESNZConstants:
    """DESNZ GHG Conversion Factors 2025."""

    bus_co2_avg_local: float  # kg CO2e/pax-km
    bus_co2_not_london: float
    bus_co2_london: float
    coach_co2: float
    car_co2_avg_diesel: float  # kg CO2e/veh-km
    car_co2_per_pax_km: float  # derived (per pax-km)
    rail_co2: float
    modal_shift_car_to_bus: float  # kg CO2e/pax-km saved switching car→bus
    car_occupancy: float


def _load_tag() -> TAGConstants:
    """Load TAG Databook v2.03fc constants from Phase 0 audit JSON."""
    with open(_AUDIT_DIR / "tag_constants.json") as f:
        data = json.load(f)
    vot = data["value_of_time"]
    src_2014 = vot["source_vot_2014_prices"]
    a131 = vot["a131_published_2023_prices"]
    carbon = data["carbon_appraisal"]
    return TAGConstants(
        vot_commuting_2014=src_2014["commuting_all_modes_per_hr"],
        vot_leisure_2014=src_2014["leisure_other_per_hr"],
        vot_business_avg_2014=src_2014["business_working_avg_per_hr"],
        vot_commuting_2023=a131["commuting_factor_cost_per_hr"],
        vot_leisure_2023=a131["leisure_factor_cost_per_hr"],
        vot_business_avg_2023=a131["working_factor_cost"],
        carbon_value_central_2010=carbon["central_2010"],
        carbon_value_central_2025=carbon["central_2025"],
        carbon_value_central_2030=carbon["central_2030"],
        social_discount_rate=data["social_discount_rate"],
    )


def _load_desnz() -> DESNZConstants:
    """Load DESNZ 2025 GHG conversion factors from Phase 0 audit JSON."""
    with open(_AUDIT_DIR / "desnz_carbon_factors.json") as f:
        data = json.load(f)
    bus = data["bus"]
    car = data["car"]
    return DESNZConstants(
        bus_co2_avg_local=bus["average_local_bus"]["value"],
        bus_co2_not_london=bus["local_bus_not_london"]["value"],
        bus_co2_london=bus["local_london_bus"]["value"],
        coach_co2=bus["coach"]["value"],
        car_co2_avg_diesel=car["average_car_diesel_per_vehicle_km"]["value"],
        car_co2_per_pax_km=car["average_car_per_passenger_km"]["value"],
        rail_co2=data["rail"]["national_rail"]["value"],
        modal_shift_car_to_bus=data["modal_shift_car_to_bus"]["saving_per_pax_km"],
        car_occupancy=car["occupancy_assumption"],
    )


@_cache
def _lazy_tag() -> TAGConstants:
    """Lazy singleton — loads once, returns cached on subsequent calls."""
    return _load_tag()


@_cache
def _lazy_desnz() -> DESNZConstants:
    """Lazy singleton — loads once, returns cached on subsequent calls."""
    return _load_desnz()


# Public API — call as TAG() and DESNZ()
TAG = _lazy_tag
DESNZ = _lazy_desnz
