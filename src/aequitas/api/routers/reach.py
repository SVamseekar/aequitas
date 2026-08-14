"""GET /api/reach — 15/30/45 destination counts for the Access exhibit."""

from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter(tags=["reach"])


@router.get("/reach")
def get_reach(
    dest_type: str = Query("jobs", pattern="^(jobs|gp|school)$"),
    cutoff: int = Query(45),
    region: str = Query("all"),
    urban_rural: str = Query("all"),
    country: str = Query("england"),
) -> dict:
    if cutoff not in (15, 30, 45):
        cutoff = 45
    from aequitas.api.services.reach_query import query_reach

    return query_reach(dest_type, cutoff, region, urban_rural, country=country)


@router.get("/reach/bands")
def get_reach_bands(
    region: str = Query("all"),
    urban_rural: str = Query("all"),
    country: str = Query("england"),
) -> dict:
    from aequitas.api.services.reach_query import query_bands

    return query_bands(region, urban_rural, country=country)
