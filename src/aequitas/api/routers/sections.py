"""Sections router — GET /api/sections."""
from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, Query

from aequitas.api.deps import get_db
from aequitas.api.models.responses import SectionItem, SectionsResponse
from aequitas.api.services.warehouse import query_sections

router = APIRouter(tags=["sections"])


@router.get("/sections", response_model=SectionsResponse)
def get_sections(
    dimension: str = Query(..., description="One of 8 dimension IDs"),
    region: str = Query("all", description="'all' or ONS region code"),
    urban_rural: str = Query("all", description="'all', 'urban', or 'rural'"),
    db: duckdb.DuckDBPyConnection | None = Depends(get_db),
) -> SectionsResponse:
    """Return sections for a given dimension."""
    if db is None:
        return SectionsResponse(dimension=dimension, sections=[])
    rows = query_sections(db, dimension, region, urban_rural)
    return SectionsResponse(
        dimension=dimension,
        sections=[SectionItem(**r) for r in rows],
    )
