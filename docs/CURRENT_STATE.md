# Aequitas — Current State (2026-08-13)

Authoritative snapshot for England score, map home, Studio, and Reach.
France is not built. **15/30/45 still unavailable** without r5py.

**Git:** no commits **mid-wave**. When we open git, PRs are **split logically**
(England 1–4, Ireland 5, packs/`time` 6, NL 7, ops 8, FR 9) — not one mega-PR.
See `docs/guidelines/git-branching.md`.

---

## 1. Product

Aequitas is a **free, multi-country bus × deprivation briefing platform**.
England is live. Other countries use the same method when their warehouses exist. Deprivation ranks stay **inside each country**.

Not a SaaS clone of Remix/TRACC. Not a 55-bar factory. Not a lock on Gini 0.5741.

## 2. Wave status

| Wave | Outcome | Status |
|------|---------|--------|
| 1 | England: §8 fixes, unique exhibits, on-page narratives, real Stage 3, `/app/:country`, landing/docs | Done |
| 2 | Map home, MapLibre, r5py 15/30/45, quoteable score | Done (map race leftover fixed with Wave 3) |
| 3 | Studio (walk-to-stop live; r5py still optional) | Done (walk-to-stop; r5py still optional) |
| 4 | Reach / Aequitas bands + research export pack | Done (service bands live; r5py 15/30/45 still optional) |
| 5 | Other countries | Later |
| 6 | Dated packs / time | Later |
| 7 | Netherlands | Later |
| 8 | Ops GTFS-RT/SIRI | Later |
| 9 | France NAP harvest + F-EDI or proxy | Later |

## 3. What works where

| Surface | What you get |
|---|---|
| `/` | Four-country landing, no “Request access”, no fake refunds |
| `/app/england` | **Map home** + in-country score + 8 doors (legacy `/dashboard/*` redirects here) |
| `/app/ireland` | Honest empty until the Ireland pack lands |
| `/app/netherlands` | Honest empty until the Netherlands pack lands |
| `/app/france` | Honest empty: pack not built yet |
| Vercel marketing | Static pages; analytics need local API |
| Pipeline Stage 3 | **Writes** equity Parquet (and mirrors policy/SHAP if present) |
| Validation | Sanity (LSOA, pop, join). Historical Gini is WARN only |

## 4. Metrics

Gini / Palma / CI are **computed** on each warehouse build from national `f1_gini`.
A June 2026 pack may still show 0.5741 until you re-run `uv run aequitas run`.
Do not treat 0.5741 as a gate.

## 5. Run locally

```bash
./scripts/dev.sh
# http://localhost:5173/app/england
uv run python scripts/smoke_local.py
```

£0 forever: no Mapbox bills, no paid routers.

## 6. Wave 2 — score, map, reach

**In-country score (0–100), one function** (`src/aequitas/analytics/score.py`):

`100 × (0.40 × pop_within_400m + 0.25 × evening_served + 0.20 × weekday_frequency_norm + 0.15 × (1 − |r|))`.
Missing terms dropped and renormalised. `GET /api/score` and `/api/overview.score` use it.
London × rural → `score: null`.

**Maps:** MapLibre + free CARTO Positron / OSM attribution. `GET /api/map`. Home is map-first.
No Mapbox.

**15 / 30 / 45:** Writer `src/aequitas/analytics/reach.py`, CLI `uv run aequitas reach`
(after `process`, hooked from `aequitas run`). Schema:
`processed/reach/lsoa_access_times.parquet` columns `lsoa, dest_type, t_15, t_30, t_45`
(destination **counts**, not Hansen). Java 17 + r5py required for a real run.

**Geographies with 15/30/45 in this checkout:** none (no Geofabrik PBF / destination Parquets
in this tree). Access and Reach show an honest sentence per missing ITL1. Do not treat empty
reach as invented 45-minute jobs.

**Compare:** `/app/england/compare` slope of 400 m %, evening isolated %, in-country score,
45-min jobs median when reach exists.

## 7. Wave 3 — Studio

Route: `/app/:country/studio` (explicit, not a dimension). Door on home keeps the query string.
Scenarios (`/app/england/scenarios`) is unchanged.

**Patch:** `StudioPatch` (`country`, `region`, `urban_rural`, `ops`, `source`). Ops:
`add_stop` | `remove_stop` | `add_trips` | `frequency_uplift`. Draw (MapLibre) and
upload (GTFS stops / GeoJSON / CSV) share that type.

**Compute:** `src/aequitas/analytics/studio.py`, CLI `uv run aequitas studio --patch file.json`.
Jobs: `POST /api/studio/jobs`, poll `GET /api/studio/jobs/{id}`, result + winners CSV.
Walk-to-stop is **live for England** when `data/processed/lsoa_centroids.parquet` exists
(ONS LSOA Dec 2021 population-weighted centroids, WGS84, joined to `lsoa_demographics`
on `lsoa_code`; region + urban/rural come from the pack, not guessed). Apply uses
warehouse stops + `compute_score` on the **active filter**. Who-gains people / IMD
deciles / area rows are real. Label stays “walk-to-stop change, not 45-minute jobs.”
Frequency / new corridor still needs r5py + PBF + BODS — we do not invent 15/30/45.
London × rural: one empty sentence.

**Centroids (not committed as a shapefile):** helper
`src/aequitas/analytics/centroids.py` downloads
[ONS PWC CSV](https://open-geography-portalx-ons.hub.arcgis.com/api/download/v1/items/32729e42d05e4e23bc7e43a36aa4ae8b/csv?layers=0)
(British National Grid `x`/`y` → EPSG:4326). First apply / `download_lsoa_centroids`
writes the parquet; warehouse table `lsoa_centroids` is sideloaded. Empty centroids
still return `needs_centroids` honestly.

**Editor:** MapLibre fits the selected ITL1 from `frontend/public/boundaries/regions.geojson`.
Clicks outside England or the selected region are rejected.

**Exports:** patch JSON + winners/losers CSV (English headers). Wave 4 research pack wraps
this; it is not a statutory BSIP submission.

## 8. Wave 4 — Reach bands + research pack

Route: `/app/:country/reach` (explicit, before `:dimensionSlug`). Door on home. Access
links here. `withSearch` keeps region / urban_rural / dest / cutoff.

**National Reach map** is the **share of people in bands 1–2 by ITL1**, not
mean/modal SQI (which painted “everything is 6”). Filtered ITL1 maps stay
**LAD modal band**. Unknown ITL1 rows are backfilled from the same LAD (Isles of
Scilly → South West); leftovers are a note, never a map feature named Unknown.

**Aequitas service band (no travel-time model)** — not TfL PTAL, never labelled
“45-minute jobs”:

- band 1: `stop_count = 0` or `no_service`
- band 2: stop nearby **and** evening isolated **and** Sunday desert
- else SQI `< 30` → 3; `< 50` → 4; `< 70` → 5; else 6

**Travel-time band** (only when `lsoa_access_times.parquet` has jobs counts for that LSOA):
band 1 if `t_45 = 0`; 2 if `t_30 = 0`; 3 if `t_30 < 10`; 4 if `t_30 < 50`; 5 if `t_15 < 20`; else 6.

Writer: `src/aequitas/analytics/bands.py` → `data/processed/reach/lsoa_access_bands.parquet`.
`GET /api/reach/bands`. Filter-sensitive. London × rural → one empty sentence.

**Hansen:** not computed. The reach parquet stores destination **counts**, not minutes.
β would be 0.05 if minutes existed (`sum dest × exp(−βt)`). Do not fake Hansen from counts.

**15/30/45:** same `reach.py` writer. CLI `uv run aequitas reach --region E12000005`.
ITL1s with times in this checkout: **none**. Destinations (`destinations_{jobs,gp,school}.parquet`)
and Geofabrik PBF are not in the tree; CLI explains and writes no invented counts.

**Research pack:** `GET /api/export/pack.csv` and `GET /api/export/pack.html` — English
headers, score, people × band × IMD decile, 400 m share, 15/30/45 or honest missing,
optional Studio job (`studio_job=`). Title: research pack, not statutory BSIP.
