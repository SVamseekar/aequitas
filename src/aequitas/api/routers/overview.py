"""Overview router — GET /api/overview."""
from __future__ import annotations

from fastapi import APIRouter, Query

from aequitas.api.deps import get_db
from aequitas.api.models.responses import (
    DimensionOverview, HeadlineStat, OverviewResponse,
)
from aequitas.api.services.warehouse import query_overview

router = APIRouter()

_DIMENSION_META = {
    "equity": ("Equity & Deprivation", "Gini coefficient", "/equity"),
    "accessibility": ("Accessibility", "Service deserts", "/accessibility"),
    "service_quality": ("Service Quality", "Mean headway", "/service-quality"),
    "route_network": ("Route Network", "Operator HHI", "/route-network"),
    "correlations": ("Socio-Economic & ML", "Top SHAP feature", "/correlations"),
    "economic": ("Economic Appraisal", "National BCR", "/economic"),
    "bus_services_act": ("Bus Services Act 2025", "Mean readiness", "/bus-services-act"),
    "scenarios": ("Policy Scenarios", "Best scenario BCR", "/scenarios"),
}


def _severity(dim_id: str, value: float) -> str:
    """Simple severity classification."""
    thresholds = {
        "equity": (0.4, 0.3),
        "accessibility": (5000, 3000),
        "service_quality": (30, 15),
    }
    high, med = thresholds.get(dim_id, (float("inf"), float("inf")))
    if value >= high:
        return "high"
    if value >= med:
        return "medium"
    return "low"


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    region: str = Query("all"),
    urban_rural: str = Query("all"),
) -> OverviewResponse:
    """Return headline stats for all 8 dimensions."""
    db = get_db()
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
