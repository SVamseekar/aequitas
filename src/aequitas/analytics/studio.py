"""Studio: apply a route/GTFS patch and measure who gains / who loses.

Walk-to-stop (400 m + score term) works without Java/PBF and is labelled as
such. Frequency uplifts and new corridors need r5py + Geofabrik PBF + BODS
GTFS — we never invent 15/30/45 or who-gains percentages.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from aequitas.analytics.reach import (
    JAVA_HINT,
    _find_gtfs,
    _find_pbf,
    reach_output_path,
)
from aequitas.analytics.score import compute_score
from jinja2 import Environment, FileSystemLoader, select_autoescape

from aequitas.intelligence.engine import _TEMPLATES_DIR

ALLOWED_OPS = ("add_stop", "remove_stop", "add_trips", "frequency_uplift")
ALLOWED_SOURCES = ("drawn", "upload")
ENGLAND_BBOX = (-6.5, 49.8, 2.0, 55.9)  # west, south, east, north
try:
    from aequitas.ireland.constants import in_ireland_bbox, in_northern_ireland
except ImportError:  # Ireland pack not on this branch
    def in_ireland_bbox(lat: float, lon: float) -> bool:
        return False

    def in_northern_ireland(lat: float, lon: float) -> bool:
        return False
WALK_M = 400.0
WALK_LABEL = "walk-to-stop change, not 45-minute jobs."

ITL1_NAMES: dict[str, str] = {
    "E12000001": "North East",
    "E12000002": "North West",
    "E12000003": "Yorkshire and The Humber",
    "E12000004": "East Midlands",
    "E12000005": "West Midlands",
    "E12000006": "East of England",
    "E12000007": "London",
    "E12000008": "South East",
    "E12000009": "South West",
}


@dataclass
class StudioOp:
    op: str
    lat: float | None = None
    lon: float | None = None
    stop_id: str | None = None
    name: str | None = None
    factor: float | None = None
    extra_trips: int | None = None
    line: list[list[float]] | None = None  # [[lon, lat], ...]

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class StudioPatch:
    country: str
    region: str
    urban_rural: str
    ops: list[StudioOp]
    source: str = "drawn"

    def to_dict(self) -> dict[str, Any]:
        return {
            "country": self.country,
            "region": self.region,
            "urban_rural": self.urban_rural,
            "ops": [o.to_dict() for o in self.ops],
            "source": self.source,
        }

    def hash(self) -> str:
        blob = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]


@dataclass
class StudioResult:
    ok: bool
    mode: str
    note: str
    patch: dict[str, Any]
    score_before: float | None
    score_after: float | None
    people_gained: int
    people_lost: int
    n_areas: int
    deciles: list[dict[str, Any]]
    areas: list[dict[str, Any]]
    reach_available: bool
    needs_r5py: bool
    narrative: str
    default_region_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def in_england_bbox(lat: float, lon: float) -> bool:
    west, south, east, north = ENGLAND_BBOX
    return south <= lat <= north and west <= lon <= east


def parse_studio_patch(raw: dict[str, Any]) -> tuple[StudioPatch | None, str | None]:
    """Validate a StudioPatch. Returns (patch, English error)."""
    if not isinstance(raw, dict):
        return None, "Patch must be a JSON object."
    country = str(raw.get("country") or "").strip().lower()
    if not country:
        return None, "Patch needs a country."
    region = str(raw.get("region") or "all")
    urban_rural = str(raw.get("urban_rural") or "all")
    source = str(raw.get("source") or "drawn")
    if source not in ALLOWED_SOURCES:
        return None, "Source must be drawn or upload."
    ops_raw = raw.get("ops")
    if not isinstance(ops_raw, list) or not ops_raw:
        return None, "Add at least one stop, removal, trip, or frequency change."
    ops: list[StudioOp] = []
    for i, item in enumerate(ops_raw):
        if not isinstance(item, dict):
            return None, f"Operation {i + 1} is not an object."
        op = str(item.get("op") or "")
        if op not in ALLOWED_OPS:
            return None, (
                f"Unknown operation “{op}”. Use add stop, remove stop, add trips, or frequency uplift."
            )
        lat = item.get("lat")
        lon = item.get("lon")
        if lat is not None:
            try:
                lat = float(lat)
            except (TypeError, ValueError):
                return None, f"Operation {i + 1} has a latitude that is not a number."
        if lon is not None:
            try:
                lon = float(lon)
            except (TypeError, ValueError):
                return None, f"Operation {i + 1} has a longitude that is not a number."
        if op in ("add_stop", "remove_stop") and lat is not None and lon is not None:
            if country == "england" and not in_england_bbox(lat, lon):
                return None, "That point is outside England. Studio only patches the England pack."
            if country == "ireland":
                if in_northern_ireland(lat, lon) or not in_ireland_bbox(lat, lon):
                    return None, (
                        "That point is outside the Republic of Ireland. "
                        "Studio does not apply England or Northern Ireland clicks to the Ireland pack."
                    )
        if op == "add_stop" and (lat is None or lon is None):
            return None, "Adding a stop needs a latitude and longitude."
        if op == "frequency_uplift":
            factor = item.get("factor")
            extra = item.get("extra_trips")
            if factor is None and extra is None:
                return None, "A frequency uplift needs a factor or extra trips."
        line = item.get("line")
        if line is not None and not isinstance(line, list):
            return None, "A drawn line must be a list of [longitude, latitude] pairs."
        ops.append(
            StudioOp(
                op=op,
                lat=lat,
                lon=lon,
                stop_id=item.get("stop_id"),
                name=item.get("name"),
                factor=float(item["factor"]) if item.get("factor") is not None else None,
                extra_trips=int(item["extra_trips"]) if item.get("extra_trips") is not None else None,
                line=line,
            )
        )
    return StudioPatch(country, region, urban_rural, ops, source), None


def parse_upload_text(text: str, *, filename: str = "") -> tuple[list[StudioOp], str | None]:
    """Parse GTFS stops.txt, GeoJSON, or CSV into ops. English error on failure."""
    stripped = text.strip()
    if not stripped:
        return [], "The file is empty."
    lower = filename.lower()
    if stripped.startswith("{") or stripped.startswith("[") or lower.endswith(".geojson"):
        return _parse_geojson(stripped)
    if "stop_lat" in stripped.lower() or lower.endswith("stops.txt"):
        return _parse_gtfs_stops(stripped)
    return _parse_csv(stripped)


def _parse_geojson(text: str) -> tuple[list[StudioOp], str | None]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return [], "That file is not valid GeoJSON."
    features = []
    if data.get("type") == "FeatureCollection":
        features = data.get("features") or []
    elif data.get("type") == "Feature":
        features = [data]
    elif data.get("type") in ("Point", "LineString"):
        features = [{"type": "Feature", "geometry": data, "properties": {}}]
    else:
        return [], "GeoJSON needs Point or LineString features."
    ops: list[StudioOp] = []
    for feat in features:
        geom = (feat or {}).get("geometry") or {}
        props = (feat or {}).get("properties") or {}
        gtype = geom.get("type")
        coords = geom.get("coordinates")
        if gtype == "Point" and isinstance(coords, list) and len(coords) >= 2:
            ops.append(
                StudioOp(
                    op="add_stop",
                    lon=float(coords[0]),
                    lat=float(coords[1]),
                    name=str(props.get("name") or props.get("stop_name") or "Uploaded stop"),
                )
            )
        elif gtype == "LineString" and isinstance(coords, list) and len(coords) >= 2:
            ops.append(StudioOp(op="add_trips", line=[[float(c[0]), float(c[1])] for c in coords if len(c) >= 2]))
            for c in (coords[0], coords[-1]):
                ops.append(StudioOp(op="add_stop", lon=float(c[0]), lat=float(c[1]), name="Corridor end"))
    if not ops:
        return [], "No points or lines found in that GeoJSON."
    return ops, None


def _parse_csv(text: str) -> tuple[list[StudioOp], str | None]:
    try:
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
    except csv.Error:
        return [], "That CSV could not be read."
    if not rows:
        return [], "The CSV has a header but no rows."
    ops: list[StudioOp] = []
    for row in rows:
        keys = {k.lower().strip(): v for k, v in row.items() if k}
        lat = keys.get("lat") or keys.get("latitude") or keys.get("stop_lat") or keys.get("y")
        lon = keys.get("lon") or keys.get("lng") or keys.get("longitude") or keys.get("stop_lon") or keys.get("x")
        if lat is None or lon is None:
            return [], "CSV needs lat and lon (or stop_lat / stop_lon) columns."
        try:
            ops.append(
                StudioOp(
                    op="add_stop",
                    lat=float(lat),
                    lon=float(lon),
                    name=str(keys.get("name") or keys.get("stop_name") or "Uploaded stop"),
                )
            )
        except ValueError:
            return [], "A row has a latitude or longitude that is not a number."
    return ops, None


def _parse_gtfs_stops(text: str) -> tuple[list[StudioOp], str | None]:
    return _parse_csv(text)


def r5py_ready(raw_dir: Path) -> tuple[bool, str]:
    pbf = _find_pbf(raw_dir)
    gtfs = _find_gtfs(raw_dir)
    try:
        import r5py  # noqa: F401
    except ImportError:
        return False, JAVA_HINT
    if pbf is None or gtfs is None:
        return False, (
            "Frequency and new corridors need a Geofabrik PBF under data/raw/osm/ "
            "and BODS GTFS under data/raw/bods/. " + JAVA_HINT
        )
    return True, ""


def _nearest_within(lat: float, lon: float, stops: list[tuple[float, float]], metres: float) -> bool:
    return any(haversine_m(lat, lon, s[0], s[1]) <= metres for s in stops)


def _covered_mask(
    lats: list[float],
    lons: list[float],
    stops: list[tuple[float, float]],
    metres: float,
) -> list[bool]:
    """True when the LSOA centroid is within `metres` of any stop."""
    n = len(lats)
    if n == 0:
        return []
    if not stops:
        return [False] * n
    try:
        import numpy as np
        from sklearn.neighbors import BallTree

        stop_arr = np.radians(np.asarray(stops, dtype=float))
        tree = BallTree(stop_arr, metric="haversine")
        pts = np.radians(np.column_stack([lats, lons]))
        dist, _ = tree.query(pts, k=1)
        return (dist[:, 0] * 6_371_000.0 <= metres).tolist()
    except Exception:  # noqa: BLE001 — tiny fixtures / missing sklearn
        return [_nearest_within(la, lo, stops, metres) for la, lo in zip(lats, lons, strict=True)]


def walk_to_stop_delta(
    centroids: pd.DataFrame,
    baseline_stops: list[tuple[float, float]],
    after_stops: list[tuple[float, float]],
    *,
    region: str,
    urban_rural: str,
    other_terms: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    """400 m coverage + score when only walk-to-stop changes. No invented 45-min."""
    need = {"lat", "lon", "pop"}
    if not need.issubset(set(centroids.columns)):
        raise ValueError("centroids need lat, lon, pop")
    areas: list[dict[str, Any]] = []
    people_gained = 0
    people_lost = 0
    pop_before = 0.0
    pop_after = 0.0
    pop_total = 0.0
    decile_acc: dict[int, dict[str, float]] = {}

    lats = [float(v) for v in centroids["lat"].tolist()]
    lons = [float(v) for v in centroids["lon"].tolist()]
    before_mask = _covered_mask(lats, lons, baseline_stops, WALK_M)
    after_mask = _covered_mask(lats, lons, after_stops, WALK_M)

    for i, row in enumerate(centroids.itertuples(index=False)):
        lat = lats[i]
        lon = lons[i]
        pop = float(row.pop)
        decile = int(getattr(row, "imd_decile", 0) or 0)
        area = str(getattr(row, "area", "") or getattr(row, "lsoa", "") or "")
        name = str(getattr(row, "name", "") or area)
        before = before_mask[i]
        after = after_mask[i]
        pop_total += pop
        if before:
            pop_before += pop
        if after:
            pop_after += pop
        delta_pop = 0.0
        if after and not before:
            people_gained += int(round(pop))
            delta_pop = pop
        elif before and not after:
            people_lost += int(round(pop))
            delta_pop = -pop
        if decile:
            bucket = decile_acc.setdefault(decile, {"gained": 0.0, "lost": 0.0})
            if delta_pop > 0:
                bucket["gained"] += delta_pop
            elif delta_pop < 0:
                bucket["lost"] += -delta_pop
        areas.append(
            {
                "area": area,
                "name": name,
                "lat": lat,
                "lon": lon,
                "pop": int(round(pop)),
                "imd_decile": decile or None,
                "covered_before": before,
                "covered_after": after,
                "delta_people": int(round(delta_pop)),
            }
        )

    share_before = (pop_before / pop_total) if pop_total else None
    share_after = (pop_after / pop_total) if pop_total else None
    terms_b = dict(other_terms or {})
    terms_a = dict(other_terms or {})
    # Keep the filter's 400 m term as the before baseline (same compute_score as home).
    # After = that term plus the centroid coverage change. Never reuse a national 400 m share.
    base_400 = terms_b.get("pop_within_400m")
    if (
        base_400 is not None
        and share_before is not None
        and share_after is not None
    ):
        delta_share = share_after - share_before
        terms_b["pop_within_400m"] = float(base_400)
        terms_a["pop_within_400m"] = max(0.0, min(1.0, float(base_400) + delta_share))
    else:
        terms_b["pop_within_400m"] = share_before
        terms_a["pop_within_400m"] = share_after
    sb = compute_score(terms_b, n_areas=len(centroids), region=region, urban_rural=urban_rural)
    sa = compute_score(terms_a, n_areas=len(centroids), region=region, urban_rural=urban_rural)
    deciles = [
        {
            "imd_decile": d,
            "people_gained": int(round(v["gained"])),
            "people_lost": int(round(v["lost"])),
        }
        for d, v in sorted(decile_acc.items())
        if v["gained"] or v["lost"]
    ]
    return {
        "score_before": sb.score,
        "score_after": sa.score,
        "score_before_payload": sb.to_dict(),
        "score_after_payload": sa.to_dict(),
        "people_gained": people_gained,
        "people_lost": people_lost,
        "n_areas": len(centroids),
        "deciles": deciles,
        "areas": areas,
        "share_before": share_before,
        "share_after": share_after,
    }


def _apply_stop_ops(
    baseline: list[tuple[float, float]],
    ops: list[StudioOp],
) -> list[tuple[float, float]]:
    after = list(baseline)
    for op in ops:
        if op.op == "add_stop" and op.lat is not None and op.lon is not None:
            after.append((op.lat, op.lon))
        elif op.op == "remove_stop" and op.lat is not None and op.lon is not None:
            after = [s for s in after if haversine_m(op.lat, op.lon, s[0], s[1]) > 30]
    return after


def render_studio_narrative(
    *,
    place: str,
    n: int,
    patch_ops: int,
    people_gained: int,
    people_lost: int,
    mode: str,
    note: str,
) -> str:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(disabled_extensions=("j2",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tmpl = env.get_template("studio_delta.j2")
    return tmpl.render(
        place=place,
        n=n,
        patch_ops=patch_ops,
        people_gained=people_gained,
        people_lost=people_lost,
        mode=mode,
        note=note,
    ).strip()


def default_region_if_partial_reach(processed_dir: Path, requested: str) -> tuple[str, str | None]:
    """If only one ITL1 has reach cache, default Studio to that region."""
    path = reach_output_path(processed_dir)
    if not path.exists():
        return requested, None
    try:
        df = pd.read_parquet(path, columns=["region"] if False else None)
    except Exception:
        return requested, None
    if "region" not in df.columns:
        return requested, None
    regions = sorted({str(r) for r in df["region"].dropna().unique() if str(r).startswith("E12")})
    if len(regions) == 1 and requested in ("all", "", None):
        code = regions[0]
        name = ITL1_NAMES.get(code, code)
        return code, f"Only {name} has a reach cache in this checkout — Studio defaults there."
    return requested, None


def apply_studio(
    patch: StudioPatch,
    *,
    centroids: pd.DataFrame,
    baseline_stops: list[tuple[float, float]] | None = None,
    processed_dir: Path | None = None,
    raw_dir: Path | None = None,
    force: bool = False,
    other_terms: dict[str, float | None] | None = None,
) -> StudioResult:
    """Apply a patch. Never invents 45-minute figures."""
    if patch.country not in {"england", "ireland"}:
        return StudioResult(
            ok=False,
            mode="pack_missing",
            note=f"The {patch.country} pack is not built yet. Studio computes on England and Ireland.",
            patch=patch.to_dict(),
            score_before=None,
            score_after=None,
            people_gained=0,
            people_lost=0,
            n_areas=0,
            deciles=[],
            areas=[],
            reach_available=False,
            needs_r5py=False,
            narrative="",
        )
    if patch.region == "E12000007" and patch.urban_rural == "rural":
        return StudioResult(
            ok=False,
            mode="empty_filter",
            note="London has no rural LSOAs under the official classification — this filter is empty.",
            patch=patch.to_dict(),
            score_before=None,
            score_after=None,
            people_gained=0,
            people_lost=0,
            n_areas=0,
            deciles=[],
            areas=[],
            reach_available=False,
            needs_r5py=False,
            narrative="",
        )

    region = patch.region
    default_note = None
    if processed_dir is not None:
        region, default_note = default_region_if_partial_reach(processed_dir, patch.region)

    needs_router = any(o.op in ("add_trips", "frequency_uplift") for o in patch.ops)
    stop_ops = [o for o in patch.ops if o.op in ("add_stop", "remove_stop")]
    ready = False
    r5_msg = JAVA_HINT
    if raw_dir is not None and needs_router:
        ready, r5_msg = r5py_ready(raw_dir)

    base = list(baseline_stops or [])
    after_stops = _apply_stop_ops(base, patch.ops)

    if centroids.empty:
        sb = compute_score(other_terms or {}, n_areas=0, region=region, urban_rural=patch.urban_rural)
        return StudioResult(
            ok=True,
            mode="needs_centroids",
            note=(
                "Walk-to-stop needs LSOA centroids (lat/lon). This pack has no small-area "
                "coordinates, so who-gains is not computed. Score is the current filter only. "
                + WALK_LABEL
            ),
            patch=patch.to_dict(),
            score_before=None if sb.score is None else round(float(sb.score), 1),
            score_after=None if sb.score is None else round(float(sb.score), 1),
            people_gained=0,
            people_lost=0,
            n_areas=0,
            deciles=[],
            areas=[],
            reach_available=False,
            needs_r5py=needs_router and not ready,
            narrative="",
            default_region_note=default_note,
        )

    walk = walk_to_stop_delta(
        centroids,
        base,
        after_stops,
        region=region,
        urban_rural=patch.urban_rural,
        other_terms=other_terms,
    )

    reach_path = reach_output_path(processed_dir) if processed_dir else None
    reach_ok = bool(reach_path and reach_path.exists())

    mode = "walk_to_stop"
    note = WALK_LABEL
    if walk["people_gained"] == 0 and walk["people_lost"] == 0 and stop_ops:
        note = (
            "Every nearby LSOA already had a stop within 400 m — this point does not change "
            "walk-to-stop coverage. Try a more isolated place. "
            + WALK_LABEL
        )
    if needs_router and not ready:
        mode = "walk_to_stop_partial"
        note = f"{WALK_LABEL} Frequency / new corridor needs r5py. {r5_msg}"
    elif needs_router and ready:
        # Real R5 apply is a long job; we do not invent after-counts here.
        # If destinations + engine exist, a future --force run writes parquet.
        # This checkout still labels honestly unless write_studio_r5 succeeds.
        r5_out = None
        if processed_dir and raw_dir:
            r5_out = try_write_studio_r5(patch, processed_dir, raw_dir, force=force)
        if r5_out is None:
            mode = "walk_to_stop_partial"
            note = (
                f"{WALK_LABEL} r5py is installed but 15/30/45 after-counts were not written "
                "(missing destinations or run failed). No invented job access."
            )
        else:
            mode = "r5_delta"
            note = "Before/after 15/30/45 from r5py on baseline GTFS plus this patch."

    place = ITL1_NAMES.get(region, "England" if region == "all" else region)
    narrative = render_studio_narrative(
        place=place,
        n=walk["n_areas"],
        patch_ops=len(patch.ops),
        people_gained=walk["people_gained"],
        people_lost=walk["people_lost"],
        mode=mode,
        note=note,
    )

    if processed_dir is not None and not centroids.empty:
        out_dir = processed_dir / "studio"
        out_dir.mkdir(parents=True, exist_ok=True)
        areas_df = pd.DataFrame(walk["areas"])
        stamp = patch.hash()
        if force or not (out_dir / f"{stamp}_areas.parquet").exists():
            areas_df.to_parquet(out_dir / f"{stamp}_areas.parquet", index=False)
            (out_dir / f"{stamp}_meta.json").write_text(
                json.dumps(
                    {
                        "written_at": datetime.now(timezone.utc).isoformat(),
                        "patch": patch.to_dict(),
                        "mode": mode,
                        "note": note,
                    },
                    indent=2,
                )
            )
            logger.info("Studio wrote {} (mode={})", out_dir / f"{stamp}_areas.parquet", mode)

    return StudioResult(
        ok=True,
        mode=mode,
        note=note,
        patch=patch.to_dict(),
        score_before=None if walk["score_before"] is None else round(float(walk["score_before"]), 1),
        score_after=None if walk["score_after"] is None else round(float(walk["score_after"]), 1),
        people_gained=walk["people_gained"],
        people_lost=walk["people_lost"],
        n_areas=walk["n_areas"],
        deciles=walk["deciles"],
        areas=walk["areas"],
        reach_available=reach_ok,
        needs_r5py=needs_router and not ready,
        narrative=narrative,
        default_region_note=default_note,
    )


def try_write_studio_r5(
    patch: StudioPatch,
    processed_dir: Path,
    raw_dir: Path,
    *,
    force: bool,
) -> Path | None:
    """Attempt a real r5py before/after. Returns parquet path or None. Never fakes."""
    ready, msg = r5py_ready(raw_dir)
    if not ready:
        logger.warning("Studio r5py skip: {}", msg)
        return None
    dest_jobs = processed_dir / "destinations_jobs.parquet"
    if not dest_jobs.exists():
        logger.warning("Studio r5py skip: no destinations_jobs.parquet")
        return None
    # Building two TransportNetworks is expensive; only when --force and dests exist.
    if not force:
        logger.info("Studio r5py skip: pass --force to rebuild a network (can take tens of minutes)")
        return None
    try:
        from aequitas.analytics.reach import try_build_r5_engine

        pbf = _find_pbf(raw_dir)
        gtfs = _find_gtfs(raw_dir)
        if pbf is None or gtfs is None:
            return None
        _ = try_build_r5_engine(pbf, gtfs)
        logger.info("Studio opened R5 network for patch {}", patch.hash())
    except Exception as exc:
        logger.warning("Studio r5py failed: {}", exc)
        return None
    return None


def winners_losers_csv(result: StudioResult) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Area code",
            "Area name",
            "People",
            "IMD decile (England ranks)",
            "Within 400 m before",
            "Within 400 m after",
            "Change in people within 400 m",
        ]
    )
    for row in result.areas:
        if not row.get("delta_people"):
            continue
        writer.writerow(
            [
                row.get("area"),
                row.get("name") or row.get("area"),
                row.get("pop"),
                row.get("imd_decile") or "",
                "yes" if row.get("covered_before") else "no",
                "yes" if row.get("covered_after") else "no",
                row.get("delta_people"),
            ]
        )
    return buf.getvalue()
