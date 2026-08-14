"""Overview router — GET /api/overview."""
from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, Query

from aequitas.api.deps import country_warehouse
from aequitas.api.models.responses import (
    DimensionOverview, HeadlineStat, OverviewResponse,
)
from aequitas.api.services.warehouse import query_overview

router = APIRouter(tags=["overview"])

# (display_name, human_label matching HEADLINE_SECTIONS stat_key, route)
_DIMENSION_META = {
    "equity": ("Equity & Deprivation", "Gini coefficient", "/equity"),
    "accessibility": ("Accessibility", "400m coverage %", "/accessibility"),
    "service_quality": ("Service Quality", "Mean SQI", "/service-quality"),
    "route_network": ("Route Network", "Operator HHI", "/route-network"),
    "correlations": ("Socio-Economic & ML", "Deprivation r", "/correlations"),
    "economic": ("Economic Appraisal", "CO₂ saving (t)", "/economic"),
    "bus_services_act": ("Bus Services Act 2025", "Avg readiness", "/bus-services-act"),
    "scenarios": ("Policy Scenarios", "Population affected", "/scenarios"),
}

_DIMENSION_META_NL = {
    "equity": ("Equity & Deprivation", "Gini (OVapi trips/capita)", "/equity"),
    "accessibility": ("Access", "400m coverage %", "/access"),
    "service_quality": ("Service", "Mean SQI (OVapi)", "/service"),
    "route_network": ("Network", "OVapi operator HHI", "/network"),
    "correlations": ("Correlations", "SES–service r", "/correlations"),
    "economic": ("Economy", "People-gap", "/economy"),
    "bus_services_act": ("Concession / OV-wet", "400m coverage %", "/policy"),
    "scenarios": ("Scenarios (OV)", "People affected", "/scenarios"),
}

_DIMENSION_META_IE = {
    "equity": ("Equity & Deprivation", "Gini (TFI trips/capita)", "/equity"),
    "accessibility": ("Access", "400m coverage %", "/access"),
    "service_quality": ("Service", "Mean SQI (TFI)", "/service"),
    "route_network": ("Network", "TFI operator HHI", "/network"),
    "correlations": ("Correlations", "HP–service r", "/correlations"),
    "economic": ("Economy (CAF/PAG)", "Illustrative EPA CO₂ (t)", "/economy"),
    "bus_services_act": ("National policy (NTA)", "400m coverage %", "/policy"),
    "scenarios": ("Scenarios (NTA)", "People affected", "/scenarios"),
}


def _severity(dim_id: str, value: float) -> str:
    """Severity bands aligned to the headline metric actually returned.

    higher_is_worse dimensions: equity (Gini), route_network (HHI), |r| for correlations.
    higher_is_better (inverted): accessibility coverage %, service SQI, readiness.
    scenarios / economic: informational — low unless extreme.
    """
    if value == 0.0:
        # Missing / empty filter combo — do not pretend a reading is "low severity".
        return "low"

    if dim_id == "equity":
        # Gini 0–1: ≥0.5 is high inequality (national bus Gini is ~0.57).
        if value >= 0.5:
            return "high"
        if value >= 0.4:
            return "medium"
        return "low"

    if dim_id == "accessibility":
        # pct_covered: low coverage is the concern.
        if value < 70.0:
            return "high"
        if value < 85.0:
            return "medium"
        return "low"

    if dim_id == "service_quality":
        # Mean SQI 0–100: low SQI is the concern.
        if value < 50.0:
            return "high"
        if value < 65.0:
            return "medium"
        return "low"

    if dim_id == "route_network":
        # Operator HHI on 0–10_000 style scale (warehouse values ~tens–thousands).
        # 84.5 is competitive → low; ≥1500 medium; ≥2500 high concentration.
        if value >= 2500:
            return "high"
        if value >= 1500:
            return "medium"
        return "low"

    if dim_id == "correlations":
        v = abs(value)
        if v >= 0.3:
            return "high"
        if v >= 0.1:
            return "medium"
        return "low"

    if dim_id == "bus_services_act":
        # Readiness 0–100: low readiness is the concern.
        if value < 30.0:
            return "high"
        if value < 50.0:
            return "medium"
        return "low"

    if dim_id == "economic":
        # CO2 saving tonnes — informational; larger savings are good (low severity).
        return "low"

    if dim_id == "scenarios":
        # Population affected — informational scale.
        return "medium" if value >= 1_000_000 else "low"

    return "low"


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    region: str = Query("all"),
    urban_rural: str = Query("all"),
    country: str = Query("england"),
    mode: str = Query("bus"),
    db: duckdb.DuckDBPyConnection | None = Depends(country_warehouse),
) -> OverviewResponse:
    """Return headline stats for all 8 dimensions."""
    if db is None:
        return OverviewResponse(
            dimensions=[
                DimensionOverview(
                    id=dim_id,
                    name=name,
                    headline_stat=HeadlineStat(value=0.0, label=label, severity="low"),
                    summary="",
                    route=route,
                )
                for dim_id, (name, label, route) in _DIMENSION_META.items()
            ],
            built_at=None,
            score=None,
            score_note="Warehouse not connected.",
        )

    built_at = None
    try:
        res = db.execute("SELECT value FROM metadata WHERE key = 'built_at'").fetchone()
        if res:
            built_at = res[0]
    except Exception:
        pass

    rows = query_overview(db, region, urban_rural)

    dimensions = []
    for row in rows:
        dim_id = row["id"]
        meta = (
            _DIMENSION_META_IE
            if country == "ireland"
            else _DIMENSION_META_NL
            if country == "netherlands"
            else _DIMENSION_META
        )
        name, label, route = meta.get(dim_id, (dim_id, "", f"/{dim_id}"))
        dimensions.append(
            DimensionOverview(
                id=dim_id,
                name=name,
                headline_stat=HeadlineStat(
                    value=row["value"],
                    label=label,
                    severity=_severity(dim_id, row["value"]),
                ),
                summary="",
                route=route,
            )
        )
    score_val = None
    score_note = None
    score_n = None
    score_dropped: list[str] = []
    try:
        from aequitas.api.services.score import score_for_filter

        scored = score_for_filter(db, region, urban_rural, mode=mode if country == "netherlands" else None)
        score_val = None if scored.score is None else round(scored.score, 1)
        score_note = scored.note
        score_n = scored.n_areas
        score_dropped = list(scored.dropped)
    except Exception:
        score_note = "Score unavailable for this filter."

    return OverviewResponse(
        dimensions=dimensions,
        built_at=built_at,
        score=score_val,
        score_note=score_note,
        score_n_areas=score_n,
        score_dropped=score_dropped,
    )
