"""Country collectors. Write a rollup file; do not touch DuckDB warehouses."""

from __future__ import annotations

import io
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

import duckdb
from loguru import logger

from aequitas.france.constants import in_fr_bbox
from aequitas.ops.fetch import FetchHit, env_key, fetch_bytes
from aequitas.ops.proto import LATE_THRESHOLD_SECONDS, TripObs, parse_feed_message
from aequitas.ops.rollup import build_rollup, imd_strip, region_strip
from aequitas.ops.store import write_rollup

BODS_GTFSRT_API = "https://data.bus-data.dft.gov.uk/api/v1/gtfsrtdatafeed/"
BODS_SIRI_API = "https://data.bus-data.dft.gov.uk/api/v1/datafeed/"
BODS_AVL_ZIP = "https://data.bus-data.dft.gov.uk/avl/download/gtfsrt"

NTA_TRIP = "https://api.nationaltransport.ie/gtfsr/v2/TripUpdates"
NTA_VP = "https://api.nationaltransport.ie/gtfsr/v2/VehiclePositions"
NTA_OPERATORS = "Dublin Bus, Bus Éireann, Go-Ahead Ireland"
NTA_IN_SCOPE = {
    "dublin bus": "Dublin Bus",
    "bus éireann": "Bus Éireann",
    "bus eireann": "Bus Éireann",
    "go-ahead ireland": "Go-Ahead Ireland",
    "go ahead ireland": "Go-Ahead Ireland",
}
# Stop codes in the NTA feed carry the operator letters used on TFI stop ids.
_NTA_STOP_AGENCY = (
    ("GAD", "Go-Ahead Ireland"),
    ("DB", "Dublin Bus"),
    ("BE", "Bus Éireann"),
)

OVAPI_TU = "https://gtfs.ovapi.nl/nl/tripUpdates.pb"
OVAPI_VP = "https://gtfs.ovapi.nl/nl/vehiclePositions.pb"

NAP_DATASETS = "https://transport.data.gouv.fr/api/datasets"

FR_RT_SAMPLE_CAP = 50
_FR_DOM_NAMES = (
    "guadeloupe",
    "martinique",
    "guyane",
    "réunion",
    "reunion",
    "mayotte",
    "saint-pierre",
    "saint-martin",
    "saint-barthélemy",
    "saint-barthelemy",
    "wallis",
    "polynésie",
    "polynesie",
    "nouvelle-calédonie",
    "nouvelle-caledonie",
)


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

    hit, siri_body = fetch_bytes(
        BODS_SIRI_API,
        entity="SIRI-VM (BODS API)",
        auth=auth,
        api_key=bods_key,
        api_key_query="api_key",
    )
    hits.append(hit)
    if siri_body:
        siri_obs = _siri_vm_delay_obs(siri_body)
        observations.extend(siri_obs)
        n_entities += len(siri_obs)

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

    n_routes = len({o.route_id for o in observations if o.route_id})
    n_with_delay = sum(1 for o in observations if o.delay_seconds is not None)
    cov = _england_coverage_sentence(
        n_updates=len(observations),
        n_routes=n_routes,
        n_static=n_static,
        n_with_delay=n_with_delay,
        key_set=bool(bods_key),
    )
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


def _england_coverage_sentence(
    *,
    n_updates: int,
    n_routes: int,
    n_static: int | None,
    n_with_delay: int,
    key_set: bool,
) -> str:
    """AVL coverage sentence. Late stays unnamed as a percentage when delay is absent."""
    if n_static:
        counts = f"{n_routes} of {n_static} static England warehouse routes saw ≥1 update"
    else:
        counts = f"{n_routes} distinct route_id values in {n_updates} updates"
    if n_with_delay == 0:
        key_note = (
            "BODS_API_KEY is unset, so TripUpdates and SIRI-VM stay closed"
            if not key_set
            else "BODS_API_KEY is set, but TripUpdates and SIRI-VM still returned no delay field"
        )
        return (
            f"BODS AVL coverage: {counts}. n_with_delay = 0, so late is —. {key_note}. "
            "The public AVL zip is VehiclePositions-style and has no stop_time_update.delay. "
            f"Late means delay > {LATE_THRESHOLD_SECONDS} seconds, and only when that field exists. "
            "This is AVL coverage, not a DfT punctuality statistic."
        )
    return (
        f"BODS snapshot: {counts}. n_with_delay = {n_with_delay}. "
        f"Late means delay > {LATE_THRESHOLD_SECONDS} seconds on TripUpdates or SIRI-VM. "
        "Not a DfT punctuality statistic. Joined to existing stop → LSOA only."
    )


_ISO_DURATION = re.compile(
    r"^P(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)$",
    re.IGNORECASE,
)


def _delay_seconds_from_text(text: str) -> int | None:
    raw = text.strip()
    if not raw:
        return None
    sign = -1 if raw.startswith("-") else 1
    body = raw[1:] if raw[0] in "+-" else raw
    if body.isdigit():
        return sign * int(body)
    match = _ISO_DURATION.match(body)
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return sign * (hours * 3600 + minutes * 60 + seconds)


_SIRI_TAG = r"(?:[\w.-]+:)?{name}"
_SIRI_DELAY = re.compile(rf"<({_SIRI_TAG.format(name='Delay')})>\s*([^<]+?)\s*</\1>", re.IGNORECASE)
_SIRI_REF = {
    name: re.compile(rf"<{_SIRI_TAG.format(name=name)}>\s*([^<]+?)\s*</(?:[\w.-]+:)?{name}>", re.IGNORECASE)
    for name in ("LineRef", "DatedVehicleJourneyRef", "VehicleJourneyRef", "StopPointRef")
}


def _siri_vm_delay_obs(body: bytes) -> list[TripObs]:
    """Keep a SIRI-VM vehicle only when a Delay element is present. Do not invent delay from clocks."""
    text = body.decode("utf-8", errors="replace")
    out: list[TripObs] = []
    for match in _SIRI_DELAY.finditer(text):
        delay = _delay_seconds_from_text(match.group(2))
        if delay is None:
            continue
        window = text[max(0, match.start() - 2500) : match.start()]
        refs = {name: rx.search(window) for name, rx in _SIRI_REF.items()}
        line = refs["LineRef"].group(1).strip() if refs["LineRef"] else None
        trip = None
        for key in ("DatedVehicleJourneyRef", "VehicleJourneyRef"):
            if refs[key]:
                trip = refs[key].group(1).strip()
                break
        stop = refs["StopPointRef"].group(1).strip() if refs["StopPointRef"] else None
        out.append(
            TripObs(
                trip_id=trip,
                route_id=line,
                stop_ids=[stop] if stop else [],
                delay_seconds=delay,
            )
        )
    return out


def _nta_agency(obs: TripObs) -> str | None:
    """Operator label from the entity id or a TFI stop code. Unknown stays None."""
    entity = (obs.entity_id or "").strip()
    named = NTA_IN_SCOPE.get(entity.casefold())
    if named:
        return named
    if entity.casefold() in {"luas", "irish rail", "iarnród éireann", "iarnrod eireann"}:
        return entity
    for stop_id in obs.stop_ids:
        code = stop_id.upper()
        match = re.search(r"\d(GAD|DB|BE)\d", code)
        if match:
            return dict(_NTA_STOP_AGENCY)[match.group(1)]
        if "LUAS" in code or re.search(r"\dIR\d", code):
            return "out of scope"
    return None


def split_nta_scope(observations: list[TripObs]) -> tuple[list[TripObs], list[str]]:
    """Keep Dublin Bus, Bus Éireann, and Go-Ahead Ireland. Log every other agency."""
    kept: list[TripObs] = []
    dropped: list[str] = []
    for obs in observations:
        agency = _nta_agency(obs)
        if agency in {"Dublin Bus", "Bus Éireann", "Go-Ahead Ireland"}:
            kept.append(obs)
            continue
        label = agency or obs.entity_id or obs.trip_id or "unknown"
        dropped.append(label)
        logger.info("NTA agency out of scope: {}", label)
    return kept, dropped


def _ireland_empty_reason(trip_status: int | None, vp_status: int | None, *, key_set: bool) -> str:
    key_note = (
        "NTA_API_KEY is set, but TripUpdates had no in-scope updates."
        if key_set
        else "NTA_API_KEY is unset."
    )
    return (
        f"Ireland NTA TripUpdates HTTP {trip_status}. VehiclePositions HTTP {vp_status}. {key_note} "
        f"Operators in scope: {NTA_OPERATORS}. No Republic-wide on-time %."
    )


def collect_ireland(project_root: Path | None = None) -> dict[str, Any]:
    hits: list[FetchHit] = []
    observations: list[TripObs] = []
    n_entities = 0
    nta_key = env_key("NTA_API_KEY", "NTA_GTFSR_KEY")
    auth = "x-api-key" if nta_key else "none"
    extra_headers = {"x-api-key": nta_key} if nta_key else None
    # VehiclePositions was HTTP 404. Do not invent a replacement URL.
    # With a key, fetch TripUpdates only. Without a key, probe both so the empty sentence can name 401 and 404.
    targets = [(NTA_TRIP, "TripUpdates (NTA)")]
    if not nta_key:
        targets.append((NTA_VP, "VehiclePositions (NTA)"))
    for url, entity in targets:
        hit, body = fetch_bytes(url, entity=entity, auth=auth, headers=extra_headers)
        hits.append(hit)
        if url == NTA_TRIP and body:
            obs, n = parse_feed_message(body)
            kept, dropped = split_nta_scope(obs)
            observations.extend(kept)
            n_entities += n
            if dropped:
                logger.info("NTA dropped {} out-of-scope entities", len(dropped))

    trip_status = next((h.status for h in hits if h.url == NTA_TRIP), None)
    vp_status = next((h.status for h in hits if h.url == NTA_VP), 404 if nta_key else None)

    if not observations:
        reason = _ireland_empty_reason(trip_status, vp_status, key_set=bool(nta_key))
        return build_rollup(
            country="ireland",
            observations=[],
            n_entities=0,
            feeds=_hits(hits),
            n_static_routes=None,
            coverage_sentence=reason,
            empty=True,
            empty_reason=reason,
            extra={"operators": NTA_OPERATORS},
        )

    cov = (
        f"NTA TripUpdates for {NTA_OPERATORS} only. "
        f"{len(observations)} in-scope updates in this snapshot. "
        "Small Area and TFI nouns stay on the static pack. Not a Republic-wide on-time %."
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
    resources: list[dict[str, str | None]] = []
    if body:
        try:
            catalog = json.loads(body.decode("utf-8", errors="replace"))
            resources = _nap_gtfsrt_urls(catalog)
        except Exception as exc:
            hit.error = f"catalog parse: {exc}"

    sampled = 0
    fetched_urls: set[str] = set()
    for res in resources:
        url = str(res["url"])
        title = str(res["title"])
        dataset_id = str(res["dataset_id"])
        if res.get("skip_reason"):
            skipped.append({"url": url, "title": title, "dataset_id": dataset_id, "reason": res["skip_reason"]})
            continue
        if sampled >= FR_RT_SAMPLE_CAP:
            skipped.append({"url": url, "title": title, "dataset_id": dataset_id, "reason": "not harvested this wave (cap)"})
            continue
        if url in fetched_urls:
            continue
        fetched_urls.add(url)
        rh, rbody = fetch_bytes(url, entity=f"gtfs-rt:{title[:80]}", auth="none", timeout=40)
        hits.append(rh)
        sampled += 1
        if rh.status in {403, 404} or rbody is None:
            skipped.append({"url": url, "title": title, "dataset_id": dataset_id, "reason": rh.error or f"HTTP {rh.status}"})
            continue
        payload = _maybe_unzip_gtfsrt(rbody)
        if not payload:
            skipped.append({"url": url, "title": title, "dataset_id": dataset_id, "reason": "empty body"})
            continue
        try:
            obs, n = parse_feed_message(payload)
        except Exception as exc:
            skipped.append({"url": url, "title": title, "dataset_id": dataset_id, "reason": f"parse: {exc}"})
            continue
        _prefix_france_ids(obs, dataset_id)
        observations.extend(obs)
        n_entities += n

    n_listed = len(resources)
    logger.info(
        "France NAP gtfs-rt listed={} sampled={} skipped={}",
        n_listed,
        sampled,
        len(skipped),
    )
    extra = {
        "n_gtfs_rt_listed": n_listed,
        "n_sampled": sampled,
        "skipped_n": len(skipped),
        "skipped_reasons": dict(Counter(str(row["reason"]) for row in skipped)),
    }
    sentence = (
        f"France NAP gtfs-rt: {n_listed} listed / {sampled} sampled / {len(skipped)} skipped. "
        "Not a national AOM figure. The sample late share is not France-wide punctuality. "
        "DOM out. Metropolitan bbox only. Coverage vs static NAP routes is — "
        "(no honest route join on this rollup)."
    )
    if not observations:
        return build_rollup(
            country="france",
            observations=[],
            n_entities=0,
            feeds=_hits(hits),
            n_static_routes=None,
            coverage_sentence=sentence,
            empty=True,
            empty_reason=sentence,
            extra=extra,
        )
    return build_rollup(
        country="france",
        observations=observations,
        n_entities=n_entities,
        feeds=_hits(hits),
        n_static_routes=None,
        coverage_sentence=sentence,
        extra=extra,
    )


def _prefix_france_ids(observations: list[TripObs], dataset_id: str) -> None:
    for obs in observations:
        if obs.trip_id:
            obs.trip_id = f"{dataset_id}:{obs.trip_id}"
        if obs.route_id:
            obs.route_id = f"{dataset_id}:{obs.route_id}"


def _france_skip_reason(dataset: dict[str, Any]) -> str | None:
    names: list[str] = [str(dataset.get("title") or "")]
    aom = dataset.get("aom")
    if isinstance(aom, dict):
        names.append(str(aom.get("name") or ""))
    covered = dataset.get("covered_area") or dataset.get("couverture")
    if isinstance(covered, dict):
        names.append(str(covered.get("name") or ""))
        coords = _geo_points(covered.get("geometry") or covered)
        if coords and not any(in_fr_bbox(lat, lon) for lon, lat in coords):
            return "outside metropolitan bbox"
    elif isinstance(covered, list):
        for item in covered:
            if isinstance(item, dict):
                names.append(str(item.get("name") or ""))
    blob = " ".join(names).casefold()
    if any(name in blob for name in _FR_DOM_NAMES):
        return "DOM out"
    return None


def _geo_points(node: Any) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []

    def walk(value: Any) -> None:
        if isinstance(value, (list, tuple)) and len(value) >= 2 and isinstance(value[0], (int, float)):
            if isinstance(value[1], (int, float)):
                points.append((float(value[0]), float(value[1])))
            return
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                walk(child)

    walk(node)
    return points


def _nap_gtfsrt_urls(catalog: Any) -> list[dict[str, str | None]]:
    datasets = catalog if isinstance(catalog, list) else catalog.get("data") or catalog.get("datasets") or []
    out: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for ds in datasets:
        if not isinstance(ds, dict):
            continue
        dataset_id = str(ds.get("id") or ds.get("datagouv_id") or ds.get("slug") or "dataset")
        title = str(ds.get("title") or dataset_id)
        skip = _france_skip_reason(ds)
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
            out.append(
                {
                    "url": url,
                    "title": f"{title} / {res.get('title') or res.get('id') or 'resource'}",
                    "dataset_id": dataset_id,
                    "skip_reason": skip,
                }
            )
    return out
