"""GET /api/map — free MapLibre choropleth payload (no paid geocoder)."""

from __future__ import annotations

from typing import Annotated, Literal

import duckdb
from fastapi import APIRouter, Depends, Query

from aequitas.api.deps import country_warehouse

router = APIRouter(tags=["map"])


@router.get("/map")
def get_map(
    region: str = Query("all"),
    urban_rural: str = Query("all"),
    country: str = Query("england"),
    mode: str | None = Query(None),
    metric: Literal["deserts", "coverage"] = Query("deserts"),
    db: Annotated[duckdb.DuckDBPyConnection | None, Depends(country_warehouse)] = None,
) -> dict:
    if db is None:
        return {
            "geography": "region",
            "metric_label": "People in deserts",
            "data": [],
            "empty": True,
            "empty_reason": "Warehouse not connected.",
        }
    from aequitas.api.services.score import map_areas_for_filter

    payload = map_areas_for_filter(
        db, region, urban_rural, mode=mode, metric=metric, country=country,
    )
    if country == "ireland" and not payload.get("empty"):
        payload["geography"] = "ireland_county"
    if country == "netherlands" and not payload.get("empty"):
        payload["geography"] = "netherlands_provincie"
    if country == "france" and not payload.get("empty"):
        payload["geography"] = "france_region"
    return payload
