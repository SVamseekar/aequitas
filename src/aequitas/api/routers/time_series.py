"""GET /api/time — same metric across dated packs."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from aequitas.warehouse.packs import extract_metrics, list_packs, resolve_pack

router = APIRouter(tags=["time"])

_METRICS = frozenset({"score", "pct_400m", "evening_isolated_pct", "mean_sqi"})


@router.get("/time")
def get_time_series(
    country: str = Query("england"),
    region: str = Query("all"),
    urban_rural: str = Query("all"),
    metric: str = Query("score"),
    pack: str | None = Query(None),
    as_of: str | None = Query(None),
) -> dict:
    key = (country or "england").strip().lower()
    requested = pack if isinstance(pack, str) else ""
    if not requested and isinstance(as_of, str):
        requested = as_of
    requested = requested.strip()
    if requested and requested.lower() not in {"current", "latest"}:
        rec = resolve_pack(key, requested)
        if rec is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown pack {requested!r} for {key}. Not falling back to the current point.",
            )
    if metric not in _METRICS:
        raise HTTPException(status_code=422, detail=f"metric must be one of {sorted(_METRICS)}")

    if region == "E12000007" and urban_rural == "rural":
        return {
            "country": key,
            "region": region,
            "urban_rural": urban_rural,
            "metric": metric,
            "area_noun": "LSOAs",
            "points": [],
            "one_date": True,
            "empty": True,
            "empty_reason": "London has no rural LSOAs under the official classification.",
            "note": "Network dates; Census 2021 / IMD 2025 frozen.",
        }

    rows = list_packs(key)
    points: list[dict] = []
    for rec in rows:
        value = None
        n_areas = rec.get("n_areas")
        wh = rec.get("warehouse")
        from pathlib import Path

        if wh and Path(wh).exists() and not (region == "all" and urban_rural == "all"):
            try:
                m = extract_metrics(Path(wh), region=region, urban_rural=urban_rural)
                value = m.get(metric)
                n_areas = m.get("n_areas")
            except Exception:
                value = rec.get(metric)
        else:
            value = rec.get(metric)
            if (value is None or (region != "all" or urban_rural != "all")) and wh and Path(wh).exists():
                try:
                    m = extract_metrics(Path(wh), region=region, urban_rural=urban_rural)
                    value = m.get(metric)
                    n_areas = m.get("n_areas")
                except Exception:
                    pass
        points.append(
            {
                "pack_id": rec.get("pack_id"),
                "as_of": rec.get("as_of") or rec.get("pack_id"),
                "value": value,
                "n_areas": n_areas,
                "current": bool(rec.get("current")),
            }
        )

    area_noun = (
        "Small Areas"
        if key == "ireland"
        else "buurten"
        if key == "netherlands"
        else "IRIS"
        if key == "france"
        else "LSOAs"
    )
    frozen = (
        "Network dates; Census 2021 / IMD 2025 frozen."
        if key == "england"
        else "Network dates; CSO Small Areas 2022 / Pobal HP 2022 frozen."
        if key == "ireland"
        else "Network dates; CBS buurten / SES-WOA frozen."
        if key == "netherlands"
        else "Network dates; IGN IRIS / F-EDI 2021 frozen. Only NAP harvest dates time-travel."
        if key == "france"
        else "Network dates; pack not built."
    )
    one_date = len(points) <= 1
    note = frozen
    if one_date:
        note = f"Only one network date in this checkout. {frozen}"
    return {
        "country": key,
        "region": region,
        "urban_rural": urban_rural,
        "metric": metric,
        "area_noun": area_noun,
        "points": points,
        "one_date": one_date,
        "empty": False,
        "empty_reason": None,
        "note": note,
        "current": (resolve_pack(key, None) or {}).get("pack_id"),
    }
