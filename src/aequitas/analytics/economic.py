"""Economic appraisal — BCR, modal shift, carbon monetisation.

Ported from Phase 0 notebook 04e.
TAG v2.03fc Dec 2025 methodology: 60-year appraisal, 3.5% discount rate.
DfT frequency elasticity: 0.55 (bus demand elasticity of frequency).
"""

from dataclasses import dataclass

from aequitas.core.constants import DESNZ, TAG


def pv_annuity(annual: float, rate: float, years: int) -> float:
    """Present value of a constant annual stream.

    PV = annual × (1 − (1+r)^-n) / r

    Args:
        annual: Annual cash flow (£).
        rate: Discount rate (e.g. 0.035 for 3.5%).
        years: Appraisal period in years.

    Returns:
        Present value (£).
    """
    if rate == 0:
        return annual * years
    return float(annual * (1 - (1 + rate) ** (-years)) / rate)


def compute_bcr(
    annual_benefit: float,
    annual_cost: float,
    rate: float | None = None,
    years: int = 60,
) -> float:
    """Benefit-Cost Ratio using TAG Green Book methodology.

    BCR = PV(benefits) / PV(costs)

    Args:
        annual_benefit: Annual monetised benefit stream (£).
        annual_cost: Annual operating cost (£).
        rate: Social discount rate (default: TAG 3.5%).
        years: Appraisal period (default: 60 years per TAG).

    Returns:
        BCR. > 1.0 = cost-beneficial.
    """
    if rate is None:
        rate = TAG().social_discount_rate
    pv_benefits = pv_annuity(annual_benefit, rate, years)
    pv_costs = pv_annuity(annual_cost, rate, years)
    return float(pv_benefits / pv_costs) if pv_costs > 0 else float("inf")


@dataclass
class ModalShiftResult:
    new_trips: float
    """Induced new bus trips from frequency improvement."""
    modal_shift_trips: float
    """Car trips replaced by bus (25% of new trips)."""
    co2_saved_tonnes: float
    """Annual CO2 saving in tonnes from modal shift."""
    vkt_reduction: float
    """Vehicle-kilometres avoided per year."""


def compute_modal_shift(
    current_annual_trips: float,
    frequency_increase_pct: float,
    elasticity: float = 0.55,
    modal_shift_fraction: float = 0.25,
    avg_trip_distance_km: float = 9.4,
) -> dict[str, float]:
    """Estimate induced demand, modal shift, and CO2 saving from frequency increase.

    Uses DfT bus demand elasticity of frequency (default 0.55).
    CO2 saving = modal_shift_trips × avg_distance × (car_co2 − bus_co2) per pax-km.

    Args:
        current_annual_trips: Baseline annual bus passenger trips.
        frequency_increase_pct: Fractional increase in service frequency (e.g. 0.20 = +20%).
        elasticity: Demand elasticity with respect to frequency (default 0.55, DfT).
        modal_shift_fraction: Fraction of new trips replacing car journeys (default 0.25).
        avg_trip_distance_km: Average trip length in km (default 9.4 km, DfT national average).

    Returns:
        Dict with keys: new_trips, modal_shift_trips, co2_saved_tonnes, vkt_reduction.
    """
    desnz = DESNZ()

    new_trips = current_annual_trips * elasticity * frequency_increase_pct
    modal_shift_trips = new_trips * modal_shift_fraction

    # CO2 saving: each shifted trip avoids car_co2 per veh-km, gains bus_co2 per pax-km
    # Net saving = (car_co2_per_pax_km − bus_co2_per_pax_km) × distance × modal_shift_trips
    co2_saving_per_pax_km = desnz.car_co2_per_pax_km - desnz.bus_co2_avg_local
    co2_saved_kg = modal_shift_trips * avg_trip_distance_km * co2_saving_per_pax_km
    co2_saved_tonnes = co2_saved_kg / 1000.0

    # VKT reduction: assume 1 car trip = 1 vehicle-km × trip_distance
    vkt_reduction = modal_shift_trips * avg_trip_distance_km

    return {
        "new_trips": float(new_trips),
        "modal_shift_trips": float(modal_shift_trips),
        "co2_saved_tonnes": float(co2_saved_tonnes),
        "vkt_reduction": float(vkt_reduction),
    }


def compute_investment_gap(
    current_trips_per_capita: float,
    national_median_trips_per_capita: float,
    population: int,
    is_urban: bool,
    annual_cost_per_trip: float = 2.50,
) -> dict[str, float]:
    """Estimate annual investment gap to reach national median service level.

    Gap trips = (national_median − current) × population (if current < median).
    Annual operating cost = gap_trips × cost_per_trip.

    Args:
        current_trips_per_capita: Current annual bus trips per capita in area.
        national_median_trips_per_capita: National median benchmark.
        population: Area population.
        is_urban: Urban=True (higher cost), rural=False.
        annual_cost_per_trip: Operating cost per additional trip (£, default £2.50).

    Returns:
        Dict with keys: gap_trips, annual_cost_gbp, above_median (bool).
    """
    # Urban areas have higher operating costs
    cost_multiplier = 1.2 if is_urban else 1.0
    adjusted_cost = annual_cost_per_trip * cost_multiplier

    if current_trips_per_capita >= national_median_trips_per_capita:
        return {
            "gap_trips": 0.0,
            "annual_cost_gbp": 0.0,
            "above_median": True,
        }

    gap_per_capita = national_median_trips_per_capita - current_trips_per_capita
    gap_trips = gap_per_capita * population
    annual_cost = gap_trips * adjusted_cost

    return {
        "gap_trips": float(gap_trips),
        "annual_cost_gbp": float(annual_cost),
        "above_median": False,
    }
