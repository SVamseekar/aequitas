"""Reach caches have no historical snapshots; never relabel current calculations."""

from __future__ import annotations

from fastapi import HTTPException, Query


def current_reach_scope(
    country: str = Query("england"),
    pack: str | None = Query(None),
    as_of: str | None = Query(None),
) -> None:
    from pathlib import Path

    from aequitas.api.deps import _live_path
    from aequitas.warehouse.packs import CURRENT_IDS, resolve_pack, warehouse_for_pack

    if country not in {"england", "ireland", "netherlands", "france"}:
        raise HTTPException(404, "Unknown country. No fallback to another country's results.")
    requested = (pack or as_of or "").strip()
    if requested.lower() in CURRENT_IDS:
        return
    record = resolve_pack(country, requested)
    live = _live_path(country)
    current = (
        record
        and record.get("current")
        and live
        and warehouse_for_pack(country, requested, live) == Path(live)
    )
    if not current:
        raise HTTPException(
            400,
            "Reach bands, destination counts and research packs use the current network only. "
            "Select the current network; historical Reach caches are unavailable.",
        )
