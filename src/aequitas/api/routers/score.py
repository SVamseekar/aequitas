"""GET /api/score — quoteable in-country score for the active filter."""

from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, Query

from aequitas.api.deps import country_warehouse
from aequitas.analytics.score import SCORE_FORMULA, compute_score

router = APIRouter(tags=["score"])


@router.get("/score")
def get_score(
    region: str = Query("all"),
    urban_rural: str = Query("all"),
    country: str = Query("england"),
    pack: str | None = Query(None),
    as_of: str | None = Query(None),
    mode: str | None = Query(None),
    db: duckdb.DuckDBPyConnection | None = Depends(country_warehouse),
) -> dict:
    pack_id = pack or as_of
    if db is None:
        empty = compute_score({}, region=region, urban_rural=urban_rural)
        payload = empty.to_dict()
        payload["formula"] = SCORE_FORMULA
        payload["pack_id"] = pack_id
        return payload
    from aequitas.api.services.score import score_for_filter

    payload = score_for_filter(db, region, urban_rural, mode=mode).to_dict()
    payload["pack_id"] = pack_id
    return payload
