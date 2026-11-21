"""Stored assistant indexes have no historical or all-mode variants."""

from pathlib import Path

from fastapi import HTTPException


def current_chat_scope(context: dict[str, object]) -> str:
    """Reject unsupported scope before retrieval or generation can relabel an index."""
    country = str(context.get("country") or "england").strip().lower()
    if country not in {"england", "ireland", "netherlands", "france"}:
        raise HTTPException(404, "Unknown assistant country. No country fallback is available.")
    if country == "netherlands" and str(context.get("mode") or "bus").lower() != "bus":
        raise HTTPException(400, "The Netherlands assistant index covers bus mode only.")
    requested = str(context.get("pack") or context.get("as_of") or "").strip()
    from aequitas.api.deps import _live_path
    from aequitas.warehouse.packs import CURRENT_IDS, resolve_pack, warehouse_for_pack

    if requested.lower() in CURRENT_IDS:
        return country
    record = resolve_pack(country, requested)
    live = _live_path(country)
    if not (
        record
        and record.get("current")
        and live
        and warehouse_for_pack(country, requested, live) == Path(live)
    ):
        raise HTTPException(
            400,
            "The assistant uses the current country index. Historical-network answers "
            "are unavailable; open the selected dated exhibits instead.",
        )
    return country
