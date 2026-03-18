"""LSOA router — GET /api/lsoa/{table}."""
from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

from aequitas.api.deps import get_db
from aequitas.api.models.responses import LsoaResponse
from aequitas.api.services.warehouse import ALLOWED_TABLES, query_lsoa

router = APIRouter(tags=["lsoa"])


@router.get("/lsoa/{table}", response_model=LsoaResponse)
def get_lsoa(
    table: str,
    region: str | None = Query(None),
    fields: str | None = Query(None, description="Comma-separated field names"),
    limit: int | None = Query(None, ge=1, le=50000),
    db: duckdb.DuckDBPyConnection | None = Depends(get_db),
) -> LsoaResponse:
    """Return LSOA-level analytics data from a named table."""
    if table not in ALLOWED_TABLES:
        raise HTTPException(400, f"Table '{table}' not allowed. Choose from: {sorted(ALLOWED_TABLES)}")
    if db is None:
        return LsoaResponse(rows=[], total=0)
    field_list = [f.strip() for f in fields.split(",")] if fields else None
    rows, total = query_lsoa(db, table, region, field_list, limit)
    return LsoaResponse(rows=rows, total=total)
