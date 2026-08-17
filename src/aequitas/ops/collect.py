"""Country collectors. Write a rollup file; do not touch DuckDB warehouses."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any

import duckdb
from loguru import logger

from aequitas.ops.fetch import FetchHit, env_key, fetch_bytes
from aequitas.ops.proto import TripObs, parse_feed_message
from aequitas.ops.rollup import build_rollup, imd_strip, region_strip
from aequitas.ops.store import write_rollup

BODS_GTFSRT_API = "https://data.bus-data.dft.gov.uk/api/v1/gtfsrtdatafeed/"
BODS_SIRI_API = "https://data.bus-data.dft.gov.uk/api/v1/datafeed/"
BODS_AVL_ZIP = "https://data.bus-data.dft.gov.uk/avl/download/gtfsrt"

NTA_TRIP = "https://api.nationaltransport.ie/gtfsr/v2/TripUpdates"
NTA_VP = "https://api.nationaltransport.ie/gtfsr/v2/VehiclePositions"
NTA_OPERATORS = "Dublin Bus, Bus Éireann, Go-Ahead Ireland"

OVAPI_TU = "https://gtfs.ovapi.nl/nl/tripUpdates.pb"
OVAPI_VP = "https://gtfs.ovapi.nl/nl/vehiclePositions.pb"

NAP_DATASETS = "https://transport.data.gouv.fr/api/datasets"

FR_RT_SAMPLE_CAP = 12


def run_ops(country: str, project_root: Path | None = None) -> Path:
    key = country.strip().lower()
    if key == "england":
        payload = collect_england(project_root)
    elif key == "ireland":
        payload = collect_ireland(project_root)
    elif key == "netherlands":
        payload = collect_netherlands(project_root)
    elif key == "france":
        payload = collect_france(project_root)
    else:
        raise ValueError(f"Unknown country {country!r}")
    dest = write_rollup(key, payload, project_root)
    logger.info("ops rollup written {} empty={} n_updates={}", dest, payload.get("empty"), payload.get("n_updates"))
    return dest


def _hits(hits: list[FetchHit]) -> list[dict[str, Any]]:
    return [h.as_dict() for h in hits]


def _maybe_unzip_gtfsrt(body: bytes) -> bytes | None:
    if body[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(body)) as zf:
            names = zf.namelist()
            # Prefer a .pb / .bin / no-ext payload
            preferred = [n for n in names if n.lower().endswith((".pb", ".bin", ".pbf", "gtfsrt"))]
            pick = preferred[0] if preferred else names[0]
            return zf.read(pick)
    return body


def collect_england(project_root: Path | None = None) -> dict[str, Any]:
    hits: list[FetchHit] = []
    observations: list[TripObs] = []
    n_entities = 0
    bods_key = env_key("BODS_API_KEY", "DFT_BODS_API_KEY")
    auth = "api_key" if bods_key else "none"

    hit, body = fetch_bytes(
        BODS_GTFSRT_API,
        entity="TripUpdates+VehiclePositions (BODS API)",
        auth=auth,
        api_key=bods_key,
        api_key_query="api_key",
    )
    hits.append(hit)
    if body:
        payload = _maybe_unzip_gtfsrt(body)
        if payload:
            obs, n = parse_feed_message(payload)
            observations.extend(obs)
            n_entities += n

    hit, _ = fetch_bytes(
        BODS_SIRI_API,
        entity="SIRI-VM (BODS API)",
        auth=auth,
        api_key=bods_key,
        api_key_query="api_key",
    )
    hits.append(hit)
    # SIRI-VM is XML vehicle locations — no delay field we trust without inventing.

    hit, body = fetch_bytes(BODS_AVL_ZIP, entity="GTFS-RT zip (BODS AVL download)", auth="none")
    hits.append(hit)
    if body:
        payload = _maybe_unzip_gtfsrt(body)
        if payload:
            obs, n = parse_feed_message(payload)
            observations.extend(obs)
            n_entities += n

    n_static, stop_lookup, route_regions = _england_lookups(project_root)
    joined_region: list[tuple[str, str, TripObs]] = []
    joined_imd: list[tuple[int, TripObs]] = []
    for o in observations:
        matched_stop = False
        for sid in o.stop_ids:
            rec = stop_lookup.get(sid)
            if not rec:
                continue
            region_code, region_name, decile = rec
            if region_code:
                joined_region.append((region_code, region_name or region_code, o))
            if decile is not None:
                joined_imd.append((int(decile), o))
            matched_stop = True
            break
        if matched_stop:
            continue
        for rname in route_regions.get(o.route_id or "", []):
            joined_region.append((rname, rname, o))

    if not observations:
        reason = (
            "England BODS GTFS-RT API and SIRI-VM returned no usable TripUpdates "
            f"(statuses {[h.status for h in hits]}). "
            "Without a BODS_API_KEY the JSON/API endpoints are 401; the public AVL zip "
            "is tried next. No punctuality invented."
        )
        return build_rollup(
            country="england",
            observations=[],
            n_entities=0,
            feeds=_hits(hits),
            n_static_routes=n_static,
            coverage_sentence=reason,
            empty=True,
            empty_reason=reason,
        )

    cov = (
        f"BODS GTFS-RT snapshot: {len(observations)} trip/vehicle updates; "
        f"{len({o.route_id for o in observations if o.route_id})} distinct route_id values. "
    )
    if n_static:
        cov += (
            f"{len({o.route_id for o in observations if o.route_id})} of {n_static} "
            "static England warehouse routes saw ≥1 update in this window. "
        )
    cov += "OGL. Late means delay > 5 minutes. Not a national BODS punctuality KPI."
    return build_rollup(
        country="england",
        observations=observations,
        n_entities=n_entities,
        feeds=_hits(hits),
        n_static_routes=n_static,
        coverage_sentence=cov,
        by_region=region_strip(joined_region),
        by_imd_decile=imd_strip(joined_imd) if joined_imd else [],
        extra={"licence": "OGL", "join": "stop_id → warehouse stops.lsoa_code / region (no Census re-download)"},
    )


def _england_lookups(
    project_root: Path | None,
) -> tuple[int | None, dict[str, tuple[str | None, str | None, int | None]], dict[str, list[str]]]:
    root = project_root or Path(__file__).resolve().parents[3]
    db_path = root / "data" / "aequitas.duckdb"
    if not db_path.is_file():
        return None, {}, {}
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        n_routes = conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
        rows = conn.execute(
            """
            SELECT s.stop_id, s.region_code, d.region, d.imd_decile
            FROM stops s
            LEFT JOIN lsoa_demographics d ON d.lsoa_cd = s.lsoa_code
            """
        ).fetchall()
        route_rows = conn.execute("SELECT route_id, regions_served FROM routes").fetchall()
    except Exception as exc:
        logger.warning("England warehouse join skipped: {}", exc)
        return None, {}, {}
    finally:
        conn.close()
    lookup: dict[str, tuple[str | None, str | None, int | None]] = {}
    for stop_id, region_code, region_name, decile in rows:
        lookup[str(stop_id)] = (region_code, region_name, int(decile) if decile is not None else None)
    route_regions: dict[str, list[str]] = {}
    for rid, served in route_rows:
        names: list[str] = []
        if isinstance(served, (list, tuple)):
            names = [str(x) for x in served if x]
        elif served:
            names = [str(served)]
        route_regions[str(rid)] = names
    return int(n_routes), lookup, route_regions


def collect_ireland(project_root: Path | None = None) -> dict[str, Any]:
    hits: list[FetchHit] = []
    observations: list[TripObs] = []
    n_entities = 0
    nta_key = env_key("NTA_API_KEY", "NTA_GTFSR_KEY")
    auth = "x-api-key" if nta_key else "none"
    extra_headers = {"x-api-key": nta_key} if nta_key else None
    for url, entity in ((NTA_TRIP, "TripUpdates (NTA)"), (NTA_VP, "VehiclePositions (NTA)")):
        hit, body = fetch_bytes(url, entity=entity, auth=auth, headers=extra_headers)
        hits.append(hit)
        if body:
            obs, n = parse_feed_message(body)
            observations.extend(obs)
            n_entities += n

    if not observations:
        reason = (
            f"Ireland NTA GTFS-RT is not in this rollup. Tried {NTA_TRIP} and {NTA_VP} "
            f"(HTTP {[h.status for h in hits]}). A free developer key is required "
            f"(NTA_API_KEY). Spec 7.3 / 7.6: only {NTA_OPERATORS}. "
            "No invented Bus Éireann rural coverage, no Republic-wide on-time %, no BODS nouns."
        )
        return build_rollup(
            country="ireland",
            observations=[],
            n_entities=0,
            feeds=_hits(hits),
            n_static_routes=None,
            coverage_sentence=reason,
            empty=True,
            empty_reason=reason,
        )

    cov = (
        f"NTA GTFS-RT for {NTA_OPERATORS} only — not the rest of the Republic. "
        f"{len(observations)} updates in this snapshot. HP/SA nouns stay on the static pack; "
        "this rollup is not IMD/LSOA."
    )
    return build_rollup(
        country="ireland",
        observations=observations,
        n_entities=n_entities,
        feeds=_hits(hits),
        n_static_routes=None,
        coverage_sentence=cov,
        extra={"operators": NTA_OPERATORS},
    )


def collect_netherlands(project_root: Path | None = None) -> dict[str, Any]:
    hits: list[FetchHit] = []
    observations: list[TripObs] = []
    n_entities = 0
    for url, entity in ((OVAPI_TU, "TripUpdates (OVapi)"), (OVAPI_VP, "VehiclePositions (OVapi)")):
        hit, body = fetch_bytes(url, entity=entity, auth="none", timeout=90)
        hits.append(hit)
        if body:
            try:
                obs, n = parse_feed_message(body)
            except Exception as exc:
                hit.error = f"parse: {exc}"
                continue
            observations.extend(obs)
            n_entities += n

    if not observations:
        reason = (
            "Netherlands OVapi RT was not parsed. "
            f"Tried {OVAPI_TU} and {OVAPI_VP} (HTTP {[h.status for h in hits]}). "
            "Static OVapi GTFS is not a punctuality feed. No city SDK scrape."
        )
        return build_rollup(
            country="netherlands",
            observations=[],
            n_entities=0,
            feeds=_hits(hits),
            n_static_routes=None,
            coverage_sentence=reason,
            empty=True,
            empty_reason=reason,
        )

    cov = (
        f"OVapi GTFS-RT snapshot ({len(observations)} updates). Mixed-mode feed; "
        "default briefing mode is bus — this rollup does not invent a bus-only punctuality split "
        "unless route_type is on the entity (it is not). SES/buurt stay on the static pack."
    )
    return build_rollup(
        country="netherlands",
        observations=observations,
        n_entities=n_entities,
        feeds=_hits(hits),
        n_static_routes=None,
        coverage_sentence=cov,
        extra={"mode_note": "RT is mixed; static briefing default remains mode=bus."},
    )


def collect_france(project_root: Path | None = None) -> dict[str, Any]:
    hits: list[FetchHit] = []
    observations: list[TripObs] = []
    n_entities = 0
    skipped: list[dict[str, Any]] = []

    hit, body = fetch_bytes(NAP_DATASETS, entity="NAP datasets catalog (gtfs-rt union)", auth="none", timeout=90)
    hits.append(hit)
    resources: list[tuple[str, str]] = []
    if body:
        try:
            catalog = json.loads(body.decode("utf-8", errors="replace"))
            resources = _nap_gtfsrt_urls(catalog)
        except Exception as exc:
            hit.error = f"catalog parse: {exc}"

    sampled = 0
    for url, title in resources:
        if sampled >= FR_RT_SAMPLE_CAP:
            skipped.append({"url": url, "title": title, "reason": "not harvested this wave (cap)"})
            continue
        rh, rbody = fetch_bytes(url, entity=f"gtfs-rt:{title[:80]}", auth="none", timeout=40)
        hits.append(rh)
        sampled += 1
        if rbody is None:
            skipped.append({"url": url, "title": title, "reason": rh.error or f"HTTP {rh.status}"})
            continue
        payload = _maybe_unzip_gtfsrt(rbody)
        if not payload:
            skipped.append({"url": url, "title": title, "reason": "empty body"})
            continue
        try:
            obs, n = parse_feed_message(payload)
        except Exception as exc:
            skipped.append({"url": url, "title": title, "reason": f"parse: {exc}"})
            continue
        observations.extend(obs)
        n_entities += n

    n_listed = len(resources)
    if not observations:
        reason = (
            f"France NAP lists {n_listed} gtfs-rt resources. This collector sampled "
            f"{sampled} and logged the rest as skipped. No usable TripUpdates in the sample "
            f"(HTTP statuses {[h.status for h in hits[:8]]}…). Incomplete is expected. "
            "No invented national punctuality. DOM out. F-EDI/IRIS stay on the static pack."
        )
        return build_rollup(
            country="france",
            observations=[],
            n_entities=0,
            feeds=_hits(hits),
            n_static_routes=None,
            coverage_sentence=reason,
            empty=True,
            empty_reason=reason,
            extra={"n_gtfs_rt_listed": n_listed, "n_sampled": sampled, "skipped_n": len(skipped)},
        )

    cov = (
        f"France NAP gtfs-rt union is incomplete. Listed {n_listed} resources; sampled "
        f"{sampled}; parsed updates={len(observations)}. Prefix collisions on trip_id/route_id "
        "already exist in the static harvest — coverage is not a national %. "
        "Missing départements are not filled. DOM out. AOM/SPC nouns stay local."
    )
    return build_rollup(
        country="france",
        observations=observations,
        n_entities=n_entities,
        feeds=_hits(hits),
        n_static_routes=None,
        coverage_sentence=cov,
        extra={"n_gtfs_rt_listed": n_listed, "n_sampled": sampled, "skipped_n": len(skipped)},
    )


def _nap_gtfsrt_urls(catalog: Any) -> list[tuple[str, str]]:
    datasets = catalog if isinstance(catalog, list) else catalog.get("data") or catalog.get("datasets") or []
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for ds in datasets:
        if not isinstance(ds, dict):
            continue
        title = str(ds.get("title") or ds.get("id") or "dataset")
        for res in ds.get("resources") or []:
            if not isinstance(res, dict):
                continue
            fmt = str(res.get("format") or "").lower()
            if fmt not in {"gtfs-rt", "gtfsrt", "gtfs_rt"}:
                continue
            url = res.get("url") or res.get("original_url")
            if not url or url in seen:
                continue
            seen.add(url)
            out.append((url, f"{title} / {res.get('title') or res.get('id') or 'resource'}"))
    return out
