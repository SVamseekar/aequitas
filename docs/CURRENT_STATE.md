# Aequitas — Current State (2026-08-13)

Authoritative snapshot after **Waves 5 and 6 stamped Done** (2026-08-13
visual pass). England Waves 1–4 remain live. Ireland **TFI × Pobal HP 2022 ×
CSO SA 2022** is on disk at CSO scale (**18,919** Small Areas). Ireland FAISS
is country-keyed (`data/ireland/faiss_index.bin`, 4,457 chunks). Wave 7
Netherlands warehouse is live (not stamped Done — PNG pass outstanding).
France is not built. **15/30/45 still unavailable** without r5py. One network
date per country — do not invent a second.

**Git:** no commits **mid-wave**. When we open git, PRs are **split logically**
(England 1–4, Ireland 5, packs/`time` 6, NL 7, ops 8, FR 9) — not one mega-PR.
See `docs/guidelines/git-branching.md`.

---

## 1. Product

Aequitas is a **free, multi-country bus × deprivation briefing platform**.
England is live. Ireland’s **doors and full pack** are live locally
(`data/aequitas_ireland.duckdb`). The Netherlands and France use the **same ten doors and
same/replace/omit catalogue** (Waves 7 and 9). Deprivation ranks stay
**inside each country**.

Not a SaaS clone of Remix/TRACC. Not a 55-bar factory. Not a lock on Gini 0.5741.

## 2. Wave status

| Wave | Outcome | Status |
|------|---------|--------|
| 1 | England: §8 fixes, unique exhibits, on-page narratives, real Stage 3, `/app/:country`, landing/docs | Done |
| 2 | Map home, MapLibre, r5py 15/30/45, quoteable score | Done (map race leftover fixed with Wave 3) |
| 3 | Studio (walk-to-stop live; r5py still optional) | Done (walk-to-stop; r5py still optional) |
| 4 | Reach / Aequitas bands + research export pack | Done (service bands live; r5py 15/30/45 still optional) |
| 5 | Ireland pack + country switcher data | **Done** (warehouse + briefing + chat). 18,919 SA. Catalogue **36 same / 12 replace / 7 omit** after CSO SAPS Theme 8 / T15 / 65+ implemented. Distinct exhibits + Insight Engine on SAME/REPLACE. FAISS[ireland] retrieves Republic narratives. |
| 6 | Monthly snapshots / refresh | **Done** (one real date each). `/time` one point + “only one network date.” Unknown pack 404s time, score, ticker. Methodology names frozen Census/HP/IMD vs monthly GTFS. |
| 7 | Netherlands + bus \| all-PT | **Done** (warehouse + briefing PNG 2026-08-14). Chat still honest empty (`FAISS[netherlands]` not built). Sunday 49.6%. National **69.6** bus / **71.1** all-PT. Home SVG provincies paint. |
| 8 | Ops GTFS-RT/SIRI | Later |
| 9 | France NAP harvest + F-EDI or proxy | Later |

## 3. What works where

| Surface | What you get |
|---|---|
| `/` | Four-country landing, no “Request access”, no fake refunds |
| `/app/england` | **Map home** + in-country score + 8 doors (legacy `/dashboard/*` redirects here) |
| `/app/ireland` | Map + score + 10 doors; 18,919 SA pack; county SVG; Ireland FAISS chat. Mistakes already paid for stay in `docs/guidelines/country-sections.md` § Ireland mistakes — **do not repeat on NL/FR.** |
| `/app/netherlands` | Warehouse + briefing live; map + 10 doors; `?mode=bus` (default) or `?mode=all`. Chat: index not built. |
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
Ireland studio: Republic bbox + SA centroids when present; Birmingham rejected.
NL / FR studio: pack not built. London × rural: one empty sentence.

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

## 9. Wave 5 — Ireland

Warehouse: `data/aequitas_ireland.duckdb` (never overwrites `data/aequitas.duckdb`).
CLI: `uv run aequitas ireland` or `uv run aequitas process --country ireland`.
API: `?country=ireland` — **no England fallback**.

Ireland warehouse: `uv run aequitas ireland` overwrites **only** `data/aequitas_ireland.duckdb`. Catalogue (`docs/guidelines/country-sections.md` / `src/aequitas/ireland/sections.py`):

| Action | Count | Notes |
|--------|------:|-------|
| same | 36 | A/B/C plus HP-swapped D/F/G; d2–d4 from CSO SAPS; bsa2 = c3 HHI |
| replace | 12 | J (CAF/PAG / EPA IE), BSA→NTA, PS Irish interventions, g5 |
| omit | 7 | d5 income, d9a–e, f3 — one sentence, no free SA variable |
| **answers** | **55** | Matches England `SECTION_REGISTRY` |

- Deprivation: Pobal HP 2022 relative index / decile. Never labelled IMD.
- Small areas: CSO SA 2022. Republic only. Northern Ireland clipped. Ticker says **Small Areas**.
- Transport: TFI `GTFS_All.zip` including **full** `stop_times`. Evening = no departure after 19:00.
- Urban/rural: density rule (≥150 people/km²), not England RUC.
- Score: same `compute_score` with HP–service gap instead of IMD.
- Economy: CAF/PAG / NTA PSO people-gap; EPA/SEAI carbon illustration; **no TAG**.
- Policy: National policy (NTA) — Connecting Ireland, BusConnects, Local Link, PSO.
- Scenarios: those Irish interventions × people / HP. € only if cited.
- Studio: Republic bbox; Birmingham click rejected; walk-to-stop uses `data/processed/ireland/sa_centroids.parquet`.
- Reach: service bands 1–6 (not TfL PTAL). 15/30/45 honest empty unless r5py ran.
- Compare: two Irish counties. **No `/app/compare-countries` page** this wave.
- Home / Access / Policy maps (seen 2026-08-13): **26 Republic county polygons**
  (SVG fill from `ireland_counties.geojson`). Earlier MapLibre-only pass painted a
  GB basemap with “boundaries could not be loaded.” Dublin vs Cork are different
  county shapes and scores (88 vs 52). Not ITL1 boxes.

**Pack on disk (2026-08-13 rebuild):**

| Fact | Value |
|------|--------|
| n Small Areas | **18,919** (CSO 2022; seed was 208) |
| Population (T1_1AGETT) | 5,149,139 |
| Counties | 26 Republic (DLR / N+S Tipperary folded) |
| National score (API terms) | ~55 from 400 m share 55.1% (freq + HP–service still in warehouse) |
| Dublin vs Cork | Dublin **5,076** SAs, 400 m **93.2%**, SQI **67.9**; Cork **2,206** SAs, 400 m **52.4%**, SQI **31.5** — scores move |
| Gini (TFI weekday trips/capita) | 0.820 (computed, not 0.5741) |
| TFI | 13,492 Republic stops; HHI **896** / 10,000; 6,008,341 `stop_times` rows |
| HP URL that worked | `https://data.gov.ie/datastore/dump/0806f07b-b514-4769-bd3d-649da87ad205` (CKAN; pobal.ie timed out). **ED-level** 3,417 rows joined SA→ED via `ED_ID_STR` (99.11%). Not invented SA deciles. SA-level HP CSV is not on data.gov.ie. |
| SA GeoJSON | `https://opendata.arcgis.com/api/v3/datasets/7ff6cde006db4a98876c58de49f108b1_0/downloads/data?format=geojson&spatialRefId=4326` (`SMALL_AREA_2022`, 18,919 features) |
| SAPS | `https://www.cso.ie/en/media/csoie/census/census2022/SAPS_2022_Small_Area_UR_171024.csv` — GUID ↔ `SA_GUID_2022`, pop = **T1_1AGETT** |
| Chat | **Ireland FAISS** `data/ireland/faiss_index.bin` (4,457 chunks from Ireland `section_results` only). Drawer on `/app/ireland` sends `context.country=ireland`. Retrieval returns TFI / Pobal HP / Small Area chunks. Invalid/missing Gemini → retrieval-only text, not England BSA. Irish Quick Actions + suggestions (no BSA/IMD). |

Wave 7 warehouse + briefing PNG pass are on disk. France is not built. `FAISS[netherlands]` is not built.

## 10. Wave 6 — dated packs + `/time`

**Layout (on disk):** `data/packs/{country}/{YYYY-MM-DD}/metrics.json` plus optional
`warehouse.duckdb`. Catalogue: `data/packs/manifest.json` (tiny; scores, 400 m %,
n areas). Live warehouses stay at `data/aequitas.duckdb` and
`data/aequitas_ireland.duckdb` and are registered as the **current** pack.

**What updates monthly:** BODS (England) / TFI (Ireland) network metrics — 400 m
coverage, evening isolation, frequency / SQI, in-country score terms that come
from GTFS.

**What stays frozen:** England Census 2021 LSOAs + population; IMD 2025 ranks;
Ireland CSO Small Areas 2022 + Pobal HP 2022. Centroids are not rewritten as if
they moved.

**Routes:** `/app/england/time`, `/app/ireland/time` (explicit, before
`:dimensionSlug`). Filter `?pack=` / `?as_of=` on score, overview, ticker,
sections. Switching country **drops** the other country’s pack id. Unknown pack
→ 404 (Ireland never silently gets England numbers).

**Refresh:** `uv run aequitas refresh` (England BODS) or
`uv run aequitas refresh --country ireland` (TFI only). Writes a dated pack,
runs sanity (LSOA ~33,755 / SA ~18,919), swaps current, keeps the previous
warehouse as `.bak` and as the prior pack folder. `--force` ignores
`min_interval_days` (25). Failed download: lock released, previous pack stays.

**launchd:** `uv run aequitas schedule-refresh` installs
`~/Library/LaunchAgents/com.aequitas.refresh.plist` (1st of month, 02:00).
Example checked in as `scripts/com.aequitas.refresh.plist.example`. No cloud
console.

**Pack dates on disk (this checkout):**

| Country | pack_id | score | 400 m % | n areas | warehouse |
|---------|---------|------:|--------:|--------:|-----------|
| England | `2026-08-01` (current) | 80.0 | 79.27 | (LSOA pack; a3 n not stored) | `data/aequitas.duckdb` |
| Ireland | `2026-08-13` (current) | 55.5 | 55.05 | 18,919 SA | `data/aequitas_ireland.duckdb` |

A second dated DuckDB appears only after a successful `aequitas refresh`.
`/time` with one date is a single point plus “only one network date in this checkout.”

**Stamp (2026-08-13):** Wave 5 and Wave 6 are **Done** after warehouse + briefing
+ Ireland FAISS + PNG pass (`qa-visual/wave56-done/`). That does **not** mean
monthly history exists or 15/30/45 ran. See §12.

## 11. What we found while finishing Waves 5 and 6

This is the measured record (API + DuckDB + screenshots). Earlier agent dumps
that said “81 loads, #root never empty” without looking at charts are **not**
this record.

### Scores and pack (re-measured 2026-08-13)

| Filter | Score | n areas | Notes |
|--------|------:|--------:|-------|
| England national | 80.0 | LSOA pack | 400 m **79.27%** |
| Ireland Republic | 55.5 | 18,919 SA | 400 m **55.05%** |
| Dublin | 88.2 | 5,076 | 400 m ~91.9% on home |
| Cork | 51.6 | 2,206 | 400 m ~50.9%; silhouette ≠ Dublin |
| Cork rural | ~15.6 | — | scores move with urban_rural |
| Leitrim | ~24.8 | — | |

Seed that almost shipped: **208** SA, score ~18.7 everywhere, Gini/SQI/HHI 0.

### CSO SAPS columns we used (do not omit these on NL/FR if CBS has them)

| section_id | SAPS | Republic r (stops/1k) |
|------------|------|----------------------:|
| d2 unemployment | Theme 8 ST + LTU / T8_1_TT | 0.010 |
| d3 no-car | T15_1_NC / T15_1_TC | 0.612 |
| d4 65+ | T1 ages 65+ / T1_1AGETT | −0.089 |

Catalogue moved **33/12/10 → 36/12/7**. Remaining omits (one sentence): d5
income, d9a–e HP domains / crime, f3 ethnicity — **no free SA column**.

### Wave 6 API (honest one-date)

| Call | Result |
|------|--------|
| `GET /api/time?country=england` | 200, one point `2026-08-01`, LSOAs, score 80 |
| `GET /api/time?country=ireland` | 200, one point `2026-08-13`, Small Areas, 55.5 |
| `?pack=2099-01-01` EN+IE | **404** — does not return the current point |
| `GET /api/score?country=ireland&pack=2026-08-01` | **404** (not England 80) |
| NL/FR `/api/time` | 200 empty, pack not built |
| Ireland export CSV/HTML | TFI, CSO SA 2022, Pobal HP, Republic. No BODS/England |
| NL/FR export | 404 |

`/time` y-axis is 0–100 so a single score point is not a hollow “0000” line.

### Chat

`data/ireland/faiss_index.bin` — **4,457** chunks from Ireland `section_results`
only. `POST /api/chat` with `context.country=ireland` retrieves TFI / HP /
Small Area text (example: b5 `r = 0.141` on Republic). Invalid Gemini →
retrieval-only. Irish Quick Actions (HP × TFI, Dublin vs Cork, NTA). No BSA/IMD.

### Pixel pass (`qa-visual/wave56-done/`)

Republic / Dublin / Cork / Cork rural / Leitrim × Home, Equity, Access,
Service, Network, Correlations, Economy, Policy, Scenarios, Reach, Studio,
Compare, Time (four chips). England home 80; London rural empty; `/economic` →
`/economy`; unknown-pack ticker = Ireland empty / unknown network date.

Home maps are **26-county SVG**, not the GB CARTO frame from the first visual
fail (`qa-visual/ie-all-home.png`). Correlations stay **4 cards** (matrix +
scatter + SHAP + omit). Economy is people-gap + illustrative EPA **250,505 t**,
no invented CAF €.

### Bugs we hit and closed (do not re-open)

| Symptom | Fix |
|---------|-----|
| 208-SA seed marked live | Rebuild 18,919; `packReady` only after two regions differ |
| a4 / c5 / a7 as `kpi_tiles` | Lorenz, scatter, people-gap bars |
| 18 Correlations cards | matrix + one scatter |
| GB map + “boundaries could not be loaded” | `geography: ireland_county` + SVG fallback |
| Export Ireland said England/BODS | Country-keyed `export_pack.py` |
| `/api/time?pack=2099` returned current point | 404 |
| Ticker “England is live” on Ireland unknown pack | `tickerForUnknownPack` |
| Chat BSA/IMD + generic Quick Actions | Irish index + Irish / hidden QA |
| `/economic` empty h1 | warehouse slugs redirect to product doors |
| TAG slider on Ireland Scenarios | England-only widget |
| Studio linked `/app/england/scenarios` | current country |
| `/time` said BODS on Ireland | TFI-only copy |
| Footer DfT on Ireland | NTA / CSO / Pobal |
| Country switch kept E12 / dublin / pack | `withSearch` drops foreign keys |
| `formatHeadline(0)` → “—” | 0 is 0.0; Palma 0.000× explained |
| c1 all-zero fake bins | empty exhibit if `stops_per_route` not stored |
| Two Vite PIDs on :5173 | blanked Choropleth — keep one listener |

Full narrative: `docs/guidelines/country-sections.md` § Ireland mistakes.

## 12. Honest holes after the stamp

- **15/30/45** empty (no r5py / Geofabrik parquet). Compare 45-min empty.
- **One pack date** each (`2026-08-01` / `2026-08-13`). `/time` is one point,
  not a monthly series. Do not invent a second date.
- **c1** stops-per-route list was never persisted; exhibit stays empty until
  TFI `stop_times` is recomputed into that list.
- **7 omits** remain (no free SA income / HP domain / crime / ethnicity).
- Economy has **no published CAF unit cost** — people-gap only.
- Gemini in this environment may be invalid; generation then retrieval-only.
- Waves **8–9** not started. France must re-check INSEE; do not copy Irish or Dutch omits.

## 13. Wave 7 — Netherlands warehouse (2026-08-14)

**Briefing PNG pass stamped** (`qa-visual/wave7-finish/`, READ 2026-08-14). Ireland-mistakes stay intact. Chat is still the honest drawer — **not** `FAISS[netherlands]`.

SVG-first choropleth (EN ITL1 + IE counties + NL provincies) so MapLibre abort is not a blank CARTO frame. Gauge synthesizes a marker from `value` if `markers` were dropped. c1/c2 persist `empty_reason: Stops-per-route list not persisted` (no zero bins). Map hook passes `mode`.

**What this PNG pass actually saw:**

| Door | region | urban_rural | mode | PNG | exhibit I SAW | number | Pass/Fail |
|------|--------|-------------|------|-----|---------------|--------|-----------|
| Home | all | all | bus | nl-nat-bus-home | NL provincie SVG **filled** + 69.6 | 69.6 / 13,827 | Pass |
| Home | all | all | all | nl-nat-all-home | 71.1 one decimal; map filled; mode All public transport | 71.1 | Pass |
| Home | noord-holland | all | bus | nl-nh-bus-home | NH silhouette filled | 75.1 | Pass |
| Home | groningen | all | bus | nl-gr-bus-home | GR silhouette filled | 64.0 | Pass |
| Home | zeeland | all | bus | nl-ze-bus-home | Zeeland filled | 52.4 | Pass |
| Home | zuid-holland | all | bus | nl-zh-bus-home | ZH filled | 72.1 | Pass |
| Home | all | rural | bus | nl-nat-rural-home | national rural 57.6 + 11 paths | 57.6 | Pass |
| Home | noord-holland | urban | bus | nl-nh-urban-home | 80.8 | 80.8 | Pass |
| Home | friesland | all | bus | nl-home-friesland | score 64.5; Fryslân silhouette filled (slug match). | 64.5 | Pass (cleanup) |
| Home | utrecht | all | bus | nl-home-utrecht | Utrecht silhouette; 77.5 | 77.5 | Pass |
| Home 390px | all | all | bus | nl-nat-bus-home-390 | 69.6 + filled map | 69.6 | Pass |
| Service | all | all | bus | nl-nat-bus-service-bars | 12 provincie SQI bars (Utrecht 50.1 … Zeeland 20.3). No Unknown. 21 leftover buurten noted. Ticker Sunday **49.6%** / 6,859. | 49.6% | Pass |
| Correlations | all | all | bus | nl-nat-bus-corr | heatmap from **z** (not all-zero); urban ~75–87 vs rural ~38–76 | n SES=10,275 | Pass |
| Network | all | all | bus | nl-nat-bus-network-gauge | HHI gauge Low/Moderate/High + pin at **1,333**; tiles 26 / Qbuzz 23.6% | 1,333 / 3,047 | Pass |
| Network c1/c2 | all | all | bus | nl-nat-bus-network-c1 | **Stops-per-route list not persisted**; P50/mean —; no zero bins | 3,047 routes | Pass (honest empty) |
| Scenarios | all | all | bus | nl-nat-bus-scenarios-bars | four people bars 11.4m / 9.9m / 6.2m / 2.2m | people | Pass |
| Compare | — | — | bus | nl-nat-bus-compare | defaults **Groningen / Noord-Holland** (not E12) | — | Pass |
| Reach | all | all | bus | nl-nat-bus-reach | honest empty; not England parquet | — | Pass |
| Time | all | all | bus | nl-nat-bus-time | one date; CBS / SES-WOA / OVapi; four chips | — | Pass |
| Chat | all | all | bus | nl-chat | “Netherlands index not built”; SES × OVapi chips | — | Pass (honest) |
| England home | — | — | — | en-home | ITL1 SVG **filled**; 80.0 | 80.0 | Pass |
| England London rural | E12000007 | rural | — | en-london-rural | empty sentence; score — | — | Pass |
| Ireland home | — | — | — | ie-home | 26-county SVG **filled**; 55.5 | 55.5 | Pass |
| Ireland Dublin / Cork | dublin / cork | — | — | notes + scores | Dublin **88.2** ≠ Cork **51.6** | — | Pass scores |
| France home | — | — | — | fr-home | pack not built | — | Pass |
| Unknown pack | pack=2099-01-01 | — | bus | nl-unknown-pack | ticker empty + 404 overview/map/ticker | 404 | Pass |

Eight-filter door matrix (Home Equity Access Service Network Correlations Economy Policy Scenarios Reach Studio Compare Time) × (nat-bus, nat-all, nh-bus, gr-bus, ze-bus, zh-bus, nat-rural, nh-urban) is on disk in `qa-visual/wave7-finish/` (104 door PNGs + provincie homes + time chips). Scores on those homes move.

Live API after rewrite (do not treat 70.6/72.0 as still true):

| Filter | score | n |
|--------|-------|---|
| NL bus national | **69.6** | 13,827 |
| NL all-PT national | **71.1** | 13,827 |
| Noord-Holland bus | **75.1** | 1,998 |
| Groningen bus | **64.0** | 594 |
| Zeeland / Utrecht / Flevoland bus | 52.4 / 77.5 / 77.3 | 431 / 928 / 385 |
| England | 80.0 | — |
| Ireland | 55.5 | 18,919 |
| Unknown pack | 404 | — |
| France | empty | — |

Sunday query: OVapi `gtfs-nl.zip` has **no `calendar.txt`**. `calendar_dates.txt` 180,442 rows, all `exception_type=1`, 17,500 Sunday dates. Joined to `stop_times` by `service_id`. A buurt is a Sunday desert iff no Sunday departure within 400 m. Bus: **6,859 / 13,827 = 49.6%**. All-PT: 6,658 / 13,827 = 48.2%. Previous 100% was the missing calendar join.

SES: rematch without imputing 0. Join **74.3%** (10,275) — earlier 70.5% + fillna(0) invented decile 5 for ~4.5k buurten and pulled national score to 70.6/72.0. Honest r on observed SES moved the deprivation term. **Do not stamp 70.6 as current.**

78 warehouse keys: 13 provincies+all × 3 stedelijkheid × 2 modes. `c1`/`c2` empty this write because stops-per-route scan was skipped to avoid a dual-mode DuckDB SIGTRAP.

**Still hollow:** `FAISS[netherlands]` not built (drawer is the correct sentence). c1/c2 stay honest-empty until a safe bus-then-append spr write.

**Cleanup (same day, not a rebuild):** Fryslân home (`?region=friesland`) paints the provincie silhouette (match GeoJSON slug `friesland`, keep dropdown **Fryslân**). Service weekday-SQI bars are 12 provincies; **21** leftover buurten with no provincie slug excluded (note on the chart). Scores unchanged: NL bus **69.6**, all-PT **71.1**, NH **75.1**, GR **64.0**, EN **80**, IE **55.5**. PNGs: `qa-visual/wave7-cleanup/`.

| Fact | Value |
|------|--------|
| Warehouse | `data/aequitas_netherlands.duckdb` (does not overwrite EN/IE) |
| n buurten | **13,827** with population > 0 (PDOK/CBS 2024 gpkg `buurten` = 14,574 incl. water / 0-pop) |
| SES-WOA | table **86092NED**, year **2023** (voorlopig). ODataFeed TypedDataSet 18,309 rows (GM+WK+BU). BU keys 14,574. Join rate **70.50%** (honest; remaining SES scores null at buurt) |
| Kerncijfers | **85984NED** 2024 — 14,574 BU. Unemployment (WW), cars/hh, 65+, income, herkomst, Wmo, labour, huur, stedelijkheid |
| Geometry | `https://geodata.cbs.nl/files/Wijkenbuurtkaart/WijkBuurtkaart_2024_v2.zip` (104 MB, layer `buurten`). Provincie SVG: cartomap provincie_2024.geojson |
| Stedelijkheid | `MateVanStedelijkheid_120` (1–5). Urban = 1–3 |
| OVapi | `https://gtfs.ovapi.nl/nl/gtfs-nl.zip` Last-Modified **2026-08-13 17:17:51 GMT**, 243,143,395 B |
| Bus stops in NL bbox | 53,157 / 53,772 (BE/DE dropped) |
| All-PT stops | 55,801 / 56,549 |
| Rail/tram/metro | present in OVapi `route_type` 0/1/2; `?mode=all` |
| HHI bus | 1,333 / 10,000 (26 agencies, 3,047 routes) |
| HHI all-PT | 1,162 / 10,000 (41 agencies, 3,316 routes) |
| Score (bus, after honest SES + calendar_dates) | National **69.6** (n=13,827); Noord-Holland **75.1** (n=1,998); Groningen **64.0** (n=594). `mode=all` **71.1**. Earlier 70.6/72.0 used imputed SES=0. NH ≠ GR. |
| Catalogue | **41 same / 12 replace / 2 omit** (d9c crime, d9d environment). CBS income/herkomst/WW used — not Ireland’s 7 omits |
| 15/30/45 | honest empty |
| Chat | `FAISS[netherlands]` not built — drawer must say so |
| Pack date | `2026-08-14` first register. One date only |

CLI: `uv run aequitas netherlands`. API: `?country=netherlands&mode=bus\|all`. Unknown pack **404**.
