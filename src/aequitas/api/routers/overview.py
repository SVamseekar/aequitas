"""Overview router — GET /api/overview."""
from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, Query

from aequitas.api.deps import get_db
from aequitas.api.models.responses import (
    DimensionOverview, HeadlineStat, OverviewResponse,
)
from aequitas.api.services.warehouse import query_overview

router = APIRouter(tags=["overview"])

_DIMENSION_META = {
    "equity": ("Equity & Deprivation", "Disparity ratio", "/equity"),
    "accessibility": ("Accessibility", "400m coverage %", "/accessibility"),
    "service_quality": ("Service Quality", "Avg trips/capita", "/service-quality"),
    "route_network": ("Route Network", "Operator HHI", "/route-network"),
    "correlations": ("Socio-Economic & ML", "Deprivation r", "/correlations"),
    "economic": ("Economic Appraisal", "CO2 saving (t)", "/economic"),
    "bus_services_act": ("Bus Services Act 2025", "Avg readiness", "/bus-services-act"),
    "scenarios": ("Policy Scenarios", "Population affected", "/scenarios"),
}


def _severity(dim_id: str, value: float) -> str:
    """Simple severity classification based on dimension-specific thresholds."""
    thresholds: dict[str, tuple[float, float]] = {
        "equity": (3.0, 2.0),        # disparity ratio
        "accessibility": (90.0, 70.0),  # % covered (inverted — high is good)
        "service_quality": (0.3, 0.15),  # trips/capita
        "route_network": (2500, 1500),   # HHI (>2500 = concentrated)
        "correlations": (0.3, 0.1),      # |r|
    }
    high, med = thresholds.get(dim_id, (float("inf"), float("inf")))
    v = abs(value) if dim_id == "correlations" else value
    if v >= high:
        return "high"
    if v >= med:
        return "medium"
    return "low"


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    region: str = Query("all"),
    urban_rural: str = Query("all"),
    db: duckdb.DuckDBPyConnection | None = Depends(get_db),
) -> OverviewResponse:
    """Return headline stats for all 8 dimensions."""
    if db is None:
        return OverviewResponse(dimensions=[
            DimensionOverview(id=dim_id, name=name, headline_stat=HeadlineStat(value=0.0, label=label, severity="low"), summary="", route=route)
            for dim_id, (name, label, route) in _DIMENSION_META.items()
        ])
    rows = query_overview(db, region, urban_rural)

    dimensions = []
    for row in rows:
        dim_id = row["id"]
        name, label, route = _DIMENSION_META.get(dim_id, (dim_id, "", f"/{dim_id}"))
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
    return OverviewResponse(dimensions=dimensions)
