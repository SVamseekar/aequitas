"""Official jobs / GP / school destination ingest (country-keyed).

Downloads are £0 official files only. A 404 is an omit — never invent rows
and never copy BRES / NHS / GIAS onto Ireland, the Netherlands, or France.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from aequitas.analytics.destinations import (
    DEST_TYPES,
    destination_path,
    validate_destination_frame,
    write_destination_frame,
)

LAT_ALIASES = ("lat", "latitude", "y", "Latitude", "LAT", "Y")
LON_ALIASES = ("lon", "lng", "longitude", "x", "Longitude", "LONG", "X", "long")
ID_ALIASES = ("dest_id", "id", "code", "ods_code", "urn", "organisationcode", "uai")
NAME_ALIASES = ("name", "label", "organisation", "establishmentname", "libelle")
AREA_ALIASES = ("area_id", "lsoa", "lsoa_code", "sa", "small_area", "buurt", "iris", "code_iris")
WEIGHT_ALIASES = ("weight", "employment_proxy", "jobs", "employment")


@dataclass
class DestinationHit:
    url: str
    status: int
    bytes: int
    rows: int = 0
    notes: str = ""


@dataclass
class OmitResult:
    written: Path | None
    omit: bool
    rows: int
    reason: str
    dest_type: str = ""
    country: str = ""


def _first_column(df: pd.DataFrame, aliases: tuple[str, ...]) -> str | None:
    lower = {c.lower(): c for c in df.columns}
    for alias in aliases:
        if alias in df.columns:
            return alias
        if alias.lower() in lower:
            return lower[alias.lower()]
    return None


def destinations_from_points(
    raw: pd.DataFrame,
    *,
    dest_type: str,
    source: str,
    country: str,
    id_prefix: str | None = None,
) -> pd.DataFrame:
    """Normalise a point table into the destination schema."""
    if dest_type not in DEST_TYPES:
        raise ValueError(f"dest_type must be one of {DEST_TYPES}")
    lat_col = _first_column(raw, LAT_ALIASES)
    lon_col = _first_column(raw, LON_ALIASES)
    if lat_col is None or lon_col is None:
        raise ValueError("point table needs lat/lon (or latitude/longitude)")
    id_col = _first_column(raw, ID_ALIASES)
    name_col = _first_column(raw, NAME_ALIASES)
    area_col = _first_column(raw, AREA_ALIASES)
    weight_col = _first_column(raw, WEIGHT_ALIASES)
    prefix = id_prefix or f"{country[:2]}-{dest_type}"
    dest_id = (
        raw[id_col].astype(str)
        if id_col is not None
        else pd.Series([f"{prefix}-{i}" for i in range(len(raw))], index=raw.index)
    )
    out = pd.DataFrame(
        {
            "dest_id": dest_id,
            "dest_type": dest_type,
            "lat": pd.to_numeric(raw[lat_col], errors="coerce"),
            "lon": pd.to_numeric(raw[lon_col], errors="coerce"),
            "name": raw[name_col].astype(str) if name_col is not None else "",
            "area_id": raw[area_col].astype(str) if area_col is not None else "",
            "weight": pd.to_numeric(raw[weight_col], errors="coerce") if weight_col is not None else 1.0,
            "source": source,
        }
    )
    out = out[out["lat"].notna() & out["lon"].notna()].reset_index(drop=True)
    issues = validate_destination_frame(out, country=country)
    if issues:
        raise ValueError(f"{country}/{dest_type} points invalid: {issues}")
    return out


def omit_if_missing(hit: DestinationHit, *, dest_type: str, country: str) -> OmitResult:
    """Record an honest omit. Never invent a replacement URL or zero-filled bins."""
    reason = f"{dest_type} omitted for {country}: HTTP {hit.status} from {hit.url}"
    if hit.bytes:
        reason += f" ({hit.bytes} B)"
    if hit.notes:
        reason += f" — {hit.notes}"
    logger.warning(reason)
    return OmitResult(
        written=None,
        omit=True,
        rows=0,
        reason=reason,
        dest_type=dest_type,
        country=country,
    )


def jobs_from_area_centroids(
    areas: pd.DataFrame,
    *,
    country: str,
    source: str,
    id_col: str,
    weight_col: str | None = None,
) -> pd.DataFrame:
    """Area-centroid jobs proxy (BRES/CBS-style). Requires lat/lon on the area table."""
    if "lat" not in areas.columns or "lon" not in areas.columns:
        raise ValueError("area table needs lat/lon centroids")
    if id_col not in areas.columns:
        raise ValueError(f"area table needs {id_col}")
    work = areas.loc[areas["lat"].notna() & areas["lon"].notna(), [id_col, "lat", "lon"]].copy()
    if weight_col and weight_col in areas.columns:
        work["weight"] = pd.to_numeric(areas.loc[work.index, weight_col], errors="coerce")
        work = work[work["weight"].notna() & (work["weight"] > 0)]
    else:
        work["weight"] = 1.0
    work = work.rename(columns={id_col: "dest_id"})
    work["name"] = work["dest_id"].astype(str)
    work["area_id"] = work["dest_id"].astype(str)
    return destinations_from_points(work, dest_type="jobs", source=source, country=country)


def catalog_file_urls(payload: dict) -> list[str]:
    """Pull downloadable resource URLs from CKAN, data.gouv, or CBS OData catalogs."""
    urls: list[str] = []
    skip_fmt = {"html", "htm", "pdf", "doc", "docx"}

    def _add(url: str, fmt: str = "") -> None:
        if not url or not str(url).startswith("http"):
            return
        if fmt.lower() in skip_fmt:
            return
        low = url.lower()
        if "pxstat" in low or "readdataset" in low:
            return
        if url not in urls:
            urls.append(url)

    resources: list[dict] = []
    if isinstance(payload.get("resources"), list):
        resources.extend(payload["resources"])
    result = payload.get("result")
    if isinstance(result, dict):
        if isinstance(result.get("resources"), list):
            resources.extend(result["resources"])
        for pkg in result.get("results") or []:
            if isinstance(pkg, dict) and isinstance(pkg.get("resources"), list):
                resources.extend(pkg["resources"])
    for item in payload.get("data") or []:
        if isinstance(item, dict) and isinstance(item.get("resources"), list):
            resources.extend(item["resources"])
    for res in resources:
        if not isinstance(res, dict):
            continue
        _add(str(res.get("url") or ""), str(res.get("format") or ""))

    for item in payload.get("value") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        url = str(item.get("url") or "")
        if name == "TypedDataSet" and url:
            _add(url, "json")
    return urls


def nabijheid_distances(raw: pd.DataFrame) -> pd.DataFrame:
    """CBS Nabijheidsstatistieken: official km to huisarts / ziekenhuis / school."""
    geo = None
    for cand in ("WijkenEnBuurten", "Codering_3", "buurt_code"):
        if cand in raw.columns:
            geo = cand
            break
    if geo is None:
        raise ValueError("nabijheid table needs a buurt code column")

    def _col(*needles: str) -> str | None:
        for c in raw.columns:
            key = str(c).lower()
            if all(n.lower() in key for n in needles):
                return c
        return None

    gp = _col("huisarts")
    hosp = _col("ziekenhuis")
    school = _col("school")
    out = pd.DataFrame({"buurt_code": raw[geo].astype(str).str.strip()})
    if gp:
        out["km_gp"] = pd.to_numeric(raw[gp], errors="coerce")
    if hosp:
        out["km_hospital"] = pd.to_numeric(raw[hosp], errors="coerce")
    if school:
        out["km_school"] = pd.to_numeric(raw[school], errors="coerce")
    out = out[out["buurt_code"].str.startswith("BU", na=False)].reset_index(drop=True)
    return out


def official_distances_path(processed_dir: Path, country: str) -> Path:
    return processed_dir / country / "official_distances.parquet"


def bpe_points(raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """INSEE BPE: Lambert-93 equipment points → WGS84 dest frames."""
    from pyproj import Transformer

    from aequitas.france.constants import FR_BBOX, LAMBERT93

    type_col = _first_column(raw, ("TYPEQU", "typequ", "TYPE", "type"))
    x_col = _first_column(raw, ("LAMBERT_X", "x", "X", "lambert_x", "COORD_X"))
    y_col = _first_column(raw, ("LAMBERT_Y", "y", "Y", "lambert_y", "COORD_Y"))
    id_col = _first_column(raw, ("AN", "id", "IDENT", "eqid"))
    if type_col is None or x_col is None or y_col is None:
        raise ValueError("BPE table needs TYPEQU and Lambert X/Y")

    work = raw.copy()
    work["_x"] = pd.to_numeric(work[x_col], errors="coerce")
    work["_y"] = pd.to_numeric(work[y_col], errors="coerce")
    work = work[work["_x"].notna() & work["_y"].notna()]
    transformer = Transformer.from_crs(LAMBERT93, "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(work["_x"].to_numpy(), work["_y"].to_numpy())
    work["lon"] = lon
    work["lat"] = lat
    west, south, east, north = FR_BBOX
    work = work[(work["lat"] >= south) & (work["lat"] <= north) & (work["lon"] >= west) & (work["lon"] <= east)]
    types = work[type_col].astype(str).str.upper()
    school_mask = types.str.match(r"^D[123]")
    gp_mask = types.eq("A504") | types.str.startswith("A50")
    frames: dict[str, pd.DataFrame] = {}
    if gp_mask.any():
        gp = work.loc[gp_mask].copy()
        if id_col:
            gp["dest_id"] = gp[id_col].astype(str)
        frames["gp"] = destinations_from_points(gp, dest_type="gp", source="INSEE BPE", country="france")
    if school_mask.any():
        sch = work.loc[school_mask].copy()
        if id_col:
            sch["dest_id"] = sch[id_col].astype(str)
        frames["school"] = destinations_from_points(sch, dest_type="school", source="INSEE BPE", country="france")
    return frames


def write_country_destinations(
    processed_dir: Path,
    country: str,
    frames: dict[str, pd.DataFrame | None],
) -> dict[str, Path]:
    """Persist only dest types that have a real frame. Missing types stay absent."""
    written: dict[str, Path] = {}
    for dest_type, df in frames.items():
        if dest_type not in DEST_TYPES:
            raise ValueError(f"dest_type must be one of {DEST_TYPES}")
        if df is None or df.empty:
            continue
        written[dest_type] = write_destination_frame(df, processed_dir, country, dest_type)
    return written


@dataclass
class IngestReport:
    country: str
    written: dict[str, Path] = field(default_factory=dict)
    omits: list[OmitResult] = field(default_factory=list)
    hits: list[DestinationHit] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "country": self.country,
            "written": {k: str(v) for k, v in self.written.items()},
            "omits": [
                {
                    "dest_type": o.dest_type,
                    "reason": o.reason,
                    "rows": o.rows,
                }
                for o in self.omits
            ],
            "hits": [
                {
                    "url": h.url,
                    "status": h.status,
                    "bytes": h.bytes,
                    "rows": h.rows,
                    "notes": h.notes,
                }
                for h in self.hits
            ],
        }


def probe_url(url: str, *, timeout: tuple[int, int] = (15, 45), retries: int = 4) -> DestinationHit:
    """HEAD, then GET if HEAD is not allowed. Retries TCP failures. Records status/bytes."""
    import time

    import requests

    last: DestinationHit | None = None
    for attempt in range(retries):
        try:
            resp = requests.head(url, timeout=timeout, allow_redirects=True)
            size = int(resp.headers.get("Content-Length") or 0)
            if resp.status_code == 405 or (resp.status_code == 200 and size == 0):
                resp = requests.get(url, timeout=timeout, allow_redirects=True, stream=True)
                size = int(resp.headers.get("Content-Length") or 0)
                resp.close()
            return DestinationHit(url=url, status=int(resp.status_code), bytes=size)
        except requests.RequestException as exc:
            last = DestinationHit(url=url, status=0, bytes=0, notes=str(exc))
            logger.warning("Probe failed {} (attempt {}): {}", url, attempt + 1, exc)
            time.sleep(1.5 * (attempt + 1))
    return last or DestinationHit(url=url, status=0, bytes=0, notes="probe failed")


# Official candidate URLs — only these are probed. Do not invent a second path
# if the first 404s; try the next listed official URL and log each hit.
ENGLAND_URLS: dict[str, tuple[str, ...]] = {
    "gp": (
        "https://files.digital.nhs.uk/assets/ods/current/epraccur.zip",
    ),
    "school": (
        "https://ea-edubase-api-prod.azurewebsites.net/edubase/downloads/public/edubasealldata.csv",
    ),
    "jobs": (),  # BRES is a Nomis extract — re-export from audit parquet when present
}

IRELAND_URLS: dict[str, tuple[str, ...]] = {
    "gp": (
        "https://data.gov.ie/api/3/action/package_search?q=HSE%20primary%20care",
        "https://data.gov.ie/api/3/action/package_search?q=general%20practitioner",
    ),
    "school": (
        "https://data.gov.ie/api/3/action/package_search?q=post-primary%20schools%20list",
        "https://data.gov.ie/api/3/action/package_search?q=department%20of%20education%20schools",
        "https://data.gov.ie/api/3/action/package_search?q=primary%20schools",
    ),
    "jobs": (
        "https://data.gov.ie/api/3/action/package_search?q=POWSCAR",
        "https://data.gov.ie/api/3/action/package_search?q=workplace%20census%20small%20area",
    ),
}

NETHERLANDS_URLS: dict[str, tuple[str, ...]] = {
    "gp": (
        "https://opendata.cbs.nl/ODataApi/OData/84718NED",
        "https://opendata.cbs.nl/ODataApi/odata/84718NED",
        "https://odata4.cbs.nl/CBS/84718NED",
        "https://opendata.cbs.nl/ODataApi/odata/80305NED",
    ),
    "school": (
        "https://opendata.cbs.nl/ODataApi/OData/84718NED",
        "https://opendata.cbs.nl/ODataApi/odata/84718NED",
    ),
    "jobs": (
        "https://opendata.cbs.nl/ODataApi/OData/85984NED",
        "https://opendata.cbs.nl/ODataApi/odata/85984NED",
    ),
}

FRANCE_URLS: dict[str, tuple[str, ...]] = {
    "gp": (
        "https://www.data.gouv.fr/api/1/datasets/?q=base%20permanente%20des%20equipements",
        "https://www.data.gouv.fr/api/1/datasets/base-permanente-des-equipements-1/",
        "https://www.data.gouv.fr/api/1/datasets/base-permanente-des-equipements-geographique-bpe/",
        "https://www.insee.fr/fr/statistiques/8217525",
    ),
    "school": (
        "https://www.insee.fr/fr/statistiques/8217525",
        "https://www.insee.fr/fr/statistiques/fichier/8217525/BPE23.zip",
    ),
    "jobs": (),
}

COUNTRY_URLS: dict[str, dict[str, tuple[str, ...]]] = {
    "england": ENGLAND_URLS,
    "ireland": IRELAND_URLS,
    "netherlands": NETHERLANDS_URLS,
    "france": FRANCE_URLS,
}


def probe_country_sources(country: str) -> list[DestinationHit]:
    urls = COUNTRY_URLS.get(country, {})
    hits: list[DestinationHit] = []
    seen: set[str] = set()
    for dest_type, candidates in urls.items():
        for url in candidates:
            if url in seen:
                continue
            seen.add(url)
            hit = probe_url(url)
            hit.notes = dest_type
            hits.append(hit)
            logger.info("Probe {} {} → HTTP {} ({} B)", country, dest_type, hit.status, hit.bytes)
    return hits


def _export_england_audit(audit_dir: Path, processed_dir: Path, report: IngestReport) -> None:
    """Re-export Phase 0 geocoded England dests when the audit parquets exist."""
    from aequitas.ingestion.poi import (
        load_employment_proxy,
        load_gp_surgeries,
        load_hospitals,
        load_schools,
    )

    mapping = (
        ("gp", audit_dir / "gp_surgeries_geocoded.parquet", load_gp_surgeries, "NHS ODS GP (Phase 0 audit)"),
        ("school", audit_dir / "schools_secondary_geocoded.parquet", load_schools, "GIAS secondary (Phase 0 audit)"),
    )
    for dest_type, path, loader, source in mapping:
        if not path.exists():
            report.omits.append(
                OmitResult(
                    written=None,
                    omit=True,
                    rows=0,
                    reason=f"{dest_type} omitted for england: {path.name} not on disk",
                    dest_type=dest_type,
                    country="england",
                )
            )
            continue
        raw = loader(path)
        frame = destinations_from_points(raw, dest_type=dest_type, source=source, country="england")
        report.written[dest_type] = write_destination_frame(frame, processed_dir, "england", dest_type)

    jobs_path = audit_dir / "lsoa_employment_proxy.parquet"
    centroids = processed_dir / "lsoa_centroids.parquet"
    if jobs_path.exists() and centroids.exists():
        jobs = load_employment_proxy(jobs_path)
        cents = pd.read_parquet(centroids)
        area_col = next((c for c in ("lsoa_code", "lsoa_cd", "lsoa") if c in jobs.columns), None)
        c_area = next((c for c in ("lsoa_code", "lsoa_cd", "lsoa") if c in cents.columns), None)
        if area_col is None or c_area is None:
            report.omits.append(
                OmitResult(
                    written=None,
                    omit=True,
                    rows=0,
                    reason="jobs omitted for england: employment proxy/centroids lack an LSOA key",
                    dest_type="jobs",
                    country="england",
                )
            )
            return
        merged = jobs.merge(cents, left_on=area_col, right_on=c_area, how="inner")
        frame = destinations_from_points(
            merged,
            dest_type="jobs",
            source="BRES 2023 MSOA→LSOA employment proxy × ONS PWC",
            country="england",
        )
        report.written["jobs"] = write_destination_frame(frame, processed_dir, "england", "jobs")
    else:
        report.omits.append(
            OmitResult(
                written=None,
                omit=True,
                rows=0,
                reason="jobs omitted for england: employment proxy or LSOA centroids missing",
                dest_type="jobs",
                country="england",
            )
        )


def _read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".zip":
        import zipfile

        with zipfile.ZipFile(path) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith((".csv", ".txt", ".xlsx"))]
            if not names:
                raise ValueError(f"{path.name} zip has no tabular member")
            member = names[0]
            with zf.open(member) as fh:
                if member.lower().endswith((".xlsx", ".xls")):
                    return pd.read_excel(fh)
                return pd.read_csv(fh, low_memory=False)
    return pd.read_csv(path, low_memory=False)


def _download_file(url: str, dest: Path) -> DestinationHit:
    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with requests.get(url, stream=True, timeout=(30, 600), allow_redirects=True) as resp:
            hit = DestinationHit(url=url, status=int(resp.status_code), bytes=int(resp.headers.get("Content-Length") or 0))
            if resp.status_code != 200:
                return hit
            tmp = dest.with_suffix(dest.suffix + ".part")
            written = 0
            with tmp.open("wb") as fh:
                for chunk in resp.iter_content(chunk_size=8 * 1024 * 1024):
                    if chunk:
                        fh.write(chunk)
                        written += len(chunk)
            tmp.replace(dest)
            hit.bytes = written
            return hit
    except requests.RequestException as exc:
        return DestinationHit(url=url, status=0, bytes=0, notes=str(exc))


def _html_file_urls(url: str) -> list[str]:
    """Follow zip/csv/xlsx hrefs on an official HTML page that already 200'd."""
    import re
    from urllib.parse import urljoin

    import requests

    try:
        resp = requests.get(url, timeout=(20, 90), allow_redirects=True)
    except requests.RequestException:
        return []
    if resp.status_code != 200:
        return []
    ctype = (resp.headers.get("Content-Type") or "").lower()
    if "html" not in ctype and not url.rstrip("/").endswith((".html", ".htm")):
        if not url.startswith("https://www.insee.fr"):
            return []
    hrefs = re.findall(r'href=["\']([^"\']+\.(?:zip|csv|xlsx|txt))', resp.text, flags=re.I)
    out: list[str] = []
    for href in hrefs:
        full = urljoin(resp.url, href)
        if full not in out:
            out.append(full)
    return out


def _maybe_json(url: str, hit: DestinationHit) -> dict | None:
    if hit.status != 200:
        return None
    import requests

    try:
        resp = requests.get(url, timeout=(20, 90), allow_redirects=True)
        if resp.status_code != 200:
            return None
        try:
            payload = resp.json()
        except ValueError:
            return None
        if isinstance(payload, dict):
            return payload
        return None
    except requests.RequestException:
        return None


def ingest_country_destinations(
    *,
    country: str,
    processed_dir: Path,
    raw_dir: Path,
    audit_dir: Path | None = None,
    probe: bool = True,
) -> IngestReport:
    """Probe official URLs, follow catalogs, write dest parquets or named omits."""
    report = IngestReport(country=country)
    raw_dest = raw_dir / country / "destinations"
    raw_dest.mkdir(parents=True, exist_ok=True)
    file_hits: list[DestinationHit] = []

    if probe:
        report.hits = probe_country_sources(country)
        follow: list[tuple[str, str]] = []
        for hit in report.hits:
            payload = _maybe_json(hit.url, hit)
            if payload:
                hit.notes = (hit.notes + " catalog").strip()
                files = catalog_file_urls(payload)
                if not files:
                    report.omits.append(
                        OmitResult(
                            written=None,
                            omit=True,
                            rows=0,
                            reason=(
                                f"{hit.notes} omitted for {country}: catalog HTTP {hit.status} "
                                f"({hit.bytes} B) had no point-file resources"
                            ),
                            dest_type=hit.notes.replace(" catalog", "").strip() or "unknown",
                            country=country,
                        )
                    )
                for file_url in files[:8]:
                    follow.append((file_url, hit.notes.replace(" catalog", "").strip() or "unknown"))
            elif hit.status != 200:
                report.omits.append(omit_if_missing(hit, dest_type=hit.notes or "unknown", country=country))
            else:
                html_files = _html_file_urls(hit.url)
                if html_files:
                    for file_url in html_files[:8]:
                        follow.append((file_url, hit.notes or "unknown"))
                else:
                    follow.append((hit.url, hit.notes or "unknown"))

        seen_files: set[str] = set()
        for file_url, dest_hint in follow:
            if file_url in seen_files:
                continue
            seen_files.add(file_url)
            name = file_url.rstrip("/").split("/")[-1].split("?")[0] or "download.bin"
            if "." not in name:
                name = f"{dest_hint}-{name}.bin"
            dest_path = raw_dest / name
            if "odata" in file_url.lower() and "TypedDataSet" in file_url:
                from aequitas.netherlands.download import _odata_pages

                pq = raw_dest / f"{dest_hint}-cbs.parquet"
                try:
                    _odata_pages(file_url, pq)
                    dest_path = pq
                    file_hit = DestinationHit(url=file_url, status=200, bytes=int(pq.stat().st_size), notes=dest_hint)
                except Exception as exc:  # noqa: BLE001
                    file_hit = DestinationHit(url=file_url, status=0, bytes=0, notes=str(exc))
            else:
                file_hit = _download_file(file_url, dest_path)
                file_hit.notes = dest_hint
            report.hits.append(file_hit)
            if file_hit.status != 200:
                report.omits.append(omit_if_missing(file_hit, dest_type=dest_hint, country=country))
                continue
            file_hits.append(file_hit)
            try:
                _ingest_downloaded(dest_path, country, dest_hint, processed_dir, report, file_hit)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Parse failed {} {}: {}", country, dest_path.name, exc)
                report.omits.append(
                    OmitResult(
                        written=None,
                        omit=True,
                        rows=0,
                        reason=f"{dest_hint} omitted for {country}: {dest_path.name} 200 but unparseable ({exc})",
                        dest_type=dest_hint,
                        country=country,
                    )
                )

    if country == "england" and audit_dir is not None:
        _export_england_audit(audit_dir, processed_dir, report)

    if raw_dest.exists():
        for dest_type in DEST_TYPES:
            if dest_type in report.written:
                continue
            matches = list(raw_dest.glob(f"*{dest_type}*.csv")) + list(raw_dest.glob(f"*{dest_type}*.parquet"))
            if not matches:
                continue
            path = matches[0]
            try:
                raw = _read_table(path)
                frame = destinations_from_points(
                    raw,
                    dest_type=dest_type,
                    source=f"local {path.name}",
                    country=country,
                )
            except ValueError as exc:
                report.omits.append(
                    OmitResult(
                        written=None,
                        omit=True,
                        rows=0,
                        reason=str(exc),
                        dest_type=dest_type,
                        country=country,
                    )
                )
                continue
            report.written[dest_type] = write_destination_frame(frame, processed_dir, country, dest_type)

    for dest_type in DEST_TYPES:
        if dest_type in report.written:
            continue
        if any(o.dest_type == dest_type for o in report.omits):
            continue
        path = destination_path(processed_dir, country, dest_type)
        if path.exists():
            continue
        report.omits.append(
            OmitResult(
                written=None,
                omit=True,
                rows=0,
                reason=(
                    f"{dest_type} omitted for {country}: no official extract on disk "
                    "and no 200 that we can parse yet"
                ),
                dest_type=dest_type,
                country=country,
            )
        )
    if report.written:
        from aequitas.analytics.destinations import compute_country_facility_400m

        compute_country_facility_400m(processed_dir, country)
    return report


def _ingest_downloaded(
    path: Path,
    country: str,
    dest_hint: str,
    processed_dir: Path,
    report: IngestReport,
    hit: DestinationHit,
) -> None:
    if country == "netherlands" and ("84718" in hit.url or dest_hint in {"gp", "school"}):
        if path.suffix.lower() not in {".json", ".parquet", ".csv"} and "odata" in hit.url.lower():
            from aequitas.netherlands.download import _odata_pages

            pq = path.with_suffix(".parquet")
            _odata_pages(hit.url, pq)
            path = pq
        raw = _read_table(path)
        if "WijkenEnBuurten" in raw.columns or any("huisarts" in c.lower() for c in raw.columns):
            dist = nabijheid_distances(raw)
            out = official_distances_path(processed_dir, "netherlands")
            out.parent.mkdir(parents=True, exist_ok=True)
            dist.to_parquet(out, index=False)
            hit.rows = int(len(dist))
            report.written.setdefault("gp", out)
            report.written.setdefault("school", out)
            logger.info("Wrote {} official distance rows → {}", len(dist), out)
            return

    if country == "france":
        raw = _read_table(path)
        if _first_column(raw, ("TYPEQU", "typequ")) and _first_column(raw, ("LAMBERT_X", "x", "X")):
            frames = bpe_points(raw)
            written = write_country_destinations(processed_dir, "france", frames)
            report.written.update(written)
            hit.rows = int(sum(len(v) for v in frames.values()))
            return

    raw = _read_table(path)
    try:
        frame = destinations_from_points(
            raw,
            dest_type=dest_hint if dest_hint in DEST_TYPES else "gp",
            source=hit.url,
            country=country,
        )
    except ValueError:
        if country == "england":
            east = _first_column(raw, ("easting", "Easting", "EASTING"))
            north = _first_column(raw, ("northing", "Northing", "NORTHING"))
            if east and north:
                from pyproj import Transformer

                t = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
                work = raw.copy()
                work["_e"] = pd.to_numeric(work[east], errors="coerce")
                work["_n"] = pd.to_numeric(work[north], errors="coerce")
                work = work[work["_e"].notna() & work["_n"].notna()]
                lon, lat = t.transform(work["_e"].to_numpy(), work["_n"].to_numpy())
                work["lon"] = lon
                work["lat"] = lat
                dest_type = dest_hint if dest_hint in DEST_TYPES else "school"
                frame = destinations_from_points(work, dest_type=dest_type, source=hit.url, country="england")
                report.written[dest_type] = write_destination_frame(frame, processed_dir, "england", dest_type)
                hit.rows = int(len(frame))
                return
        raise
    if country == "ireland":
        from aequitas.ireland.constants import in_ireland_bbox, in_northern_ireland

        keep = []
        for la, lo in zip(frame["lat"].tolist(), frame["lon"].tolist(), strict=True):
            keep.append(in_ireland_bbox(float(la), float(lo)) and not in_northern_ireland(float(la), float(lo)))
        frame = frame.loc[keep].reset_index(drop=True)
        if frame.empty:
            raise ValueError("no Republic points after NI clip")
    dest_type = str(frame["dest_type"].iloc[0])
    report.written[dest_type] = write_destination_frame(frame, processed_dir, country, dest_type)
    hit.rows = int(len(frame))
