"""LSOA router — GET /api/lsoa/{table}."""
from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

from aequitas.api.deps import get_db
from aequitas.api.models.responses import LsoaResponse
from aequitas.api.services.warehouse import ALLOWED_TABLES, query_lsoa, resolve_lsoa_table

router = APIRouter(tags=["lsoa"])


@router.get("/lsoa/{table}", response_model=LsoaResponse)
def get_lsoa(
    table: str,
    region: str | None = Query(None),
    fields: str | None = Query(None, description="Comma-separated field names"),
    limit: int | None = Query(None, ge=1, le=50000),
    db: duckdb.DuckDBPyConnection | None = Depends(get_db),
) -> LsoaResponse:
    """Return LSOA-level analytics data from a named table.

    Allowed tables match the live warehouse catalog. Legacy names are aliased.
    Missing tables return empty rows (200), never 500 CatalogException.
    """
    try:
        resolve_lsoa_table(table)
    except ValueError:
        raise HTTPException(
            400,
            f"Table '{table}' not allowed. Choose from: {sorted(ALLOWED_TABLES)}",
        ) from None

    if db is None:
        return LsoaResponse(rows=[], total=0)

    field_list = [f.strip() for f in fields.split(",")] if fields else None
    try:
        rows, total = query_lsoa(db, table, region, field_list, limit)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return LsoaResponse(rows=rows, total=total)
