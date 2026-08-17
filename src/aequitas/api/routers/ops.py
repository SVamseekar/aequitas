"""GET /api/ops — last collector rollup only (D01: no protobuf in the handler)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from aequitas.ops.store import COUNTRIES, load_latest_rollup
from aequitas.warehouse.packs import resolve_pack

router = APIRouter(tags=["ops"])


@router.get("/ops")
def get_ops(
    country: str = Query("england"),
    pack: str | None = Query(None),
    as_of: str | None = Query(None),
) -> dict:
    key = (country or "england").strip().lower()
    if key not in COUNTRIES:
        raise HTTPException(status_code=404, detail=f"Unknown country {key!r}.")

    requested = (pack or as_of or "").strip()
    if requested and requested.lower() not in {"current", "latest"}:
        rec = resolve_pack(key, requested)
        if rec is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown pack {requested!r} for {key}. Ops is not time-travelled.",
            )

    rollup = load_latest_rollup(key)
    if rollup is None:
        raise HTTPException(
            status_code=404,
            detail=f"No ops rollup for {key}. Run `uv run aequitas ops --country {key}`.",
        )
    return rollup
