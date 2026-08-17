# Wave 8 ops — source log

Fetched **2026-08-17**. Only URLs actually hit. Status and bytes are measured.
No invented second URL. No paid Swiftly / CitySwift / Google. Rollups live in
`data/ops/{country}/latest.json` (gitignored). Static DuckDB files were not written.

Late threshold used when `delay` is present: **> 300 seconds (5 minutes)**.
A snapshot is not “live to the second.”

## England — BODS (OGL)

| URL | Entity | Auth | HTTP | Bytes | Notes |
|-----|--------|------|------|------:|-------|
| `https://data.bus-data.dft.gov.uk/api/v1/gtfsrtdatafeed/` | TripUpdates + VehiclePositions API | none (`BODS_API_KEY` unset) | **401** | 6 | Do not invent a second path |
| `https://data.bus-data.dft.gov.uk/api/v1/datafeed/` | SIRI-VM API | none | **401** | 6 | Same key gate |
| `https://data.bus-data.dft.gov.uk/avl/download/gtfsrt` | GTFS-RT zip (AVL download) | none | **200** (302 → signed `download.bus-data.dft.gov.uk`) | **1,651,324** | VehiclePositions-style feed |

**Rollup (this checkout):** `n_updates=25063`, `n_entities=25063`, `n_with_delay=0` (this zip has no `stop_time_update.delay`), `n_skipped=0`, `n_cancelled=0`, `n_routes_with_update=5351` of **13640** static warehouse routes → **coverage 39.23%**. Region strip joined via `routes.regions_served` (9 ITL1 names). IMD decile empty — no stop_ids on the AVL entities. **Not** a national punctuality KPI.

## Ireland — NTA (spec 7.3 / 7.6)

Operators in scope: **Dublin Bus, Bus Éireann, Go-Ahead Ireland only**.

| URL | Entity | Auth | HTTP | Bytes | Notes |
|-----|--------|------|------|------:|-------|
| `https://api.nationaltransport.ie/gtfsr/v2/TripUpdates` | TripUpdates | none (`NTA_API_KEY` unset) | **401** | 152 | Access Denied |
| `https://api.nationaltransport.ie/gtfsr/v2/VehiclePositions` | VehiclePositions | none | **404** | 54 | Do not invent a replacement path |

**Rollup:** honest empty. No 0% on-time. No Republic-wide coverage. No BODS / IMD / LSOA nouns.

## Netherlands — OVapi

| URL | Entity | Auth | HTTP | Bytes | Notes |
|-----|--------|------|------|------:|-------|
| `https://gtfs.ovapi.nl/` | portal HTML | none | **200** | — | Index only |
| `https://gtfs.ovapi.nl/nl/tripUpdates.pb` | TripUpdates | none | **200** | **4,604,050** | Parsed |
| `https://gtfs.ovapi.nl/nl/vehiclePositions.pb` | VehiclePositions | none | **200** | **545,113** | Parsed |

**Rollup:** `n_updates=14789`, `n_with_delay=10105`, `pct_late=1.3`, `n_skipped=5423`, `n_routes_with_update=1346`. Mixed-mode feed; static briefing default remains `mode=bus`. No SES/buurt invented on this rollup. No static route table in the NL warehouse, so coverage % vs timetable routes is **not** claimed.

## France — NAP gtfs-rt union

| URL | Entity | Auth | HTTP | Bytes | Notes |
|-----|--------|------|------|------:|-------|
| `https://transport.data.gouv.fr/api/datasets` | catalog | none | **200** | **2,479,296** | Client-side `format=gtfs-rt` filter. **380** gtfs-rt resources listed |

Sampled first **12** listed resources this wave (cap). **370** skipped as “not harvested this wave.” Incomplete is expected (france-sources.md already noted ~380 RT not harvested).

Hits inside the sample (2026-08-17):

| HTTP | Resource (title truncated) |
|------|----------------------------|
| 200 | Eurostar temps réel (`data.gouv.fr` resource) |
| 200 | Trenitalia France GTFS-RT (NAP proxy) |
| 200 | SNCF service-alerts |
| 200 | SNCF trip-updates |
| 403 | liO Occitanie (two resources) — skipped, not retried with another URL |
| 200 | Proximité ZOU! bus RT |

**Rollup:** `n_updates=3610`, `n_with_delay=2815`, `pct_late=16.2`, `n_skipped=126`, `n_routes_with_update=22`. This is **not** a national AOM punctuality figure. Prefix collisions on `trip_id`/`route_id` already exist in the static harvest. DOM out. F-EDI / IRIS stay on the static pack.

## Env keys (optional, never committed)

See `.env.example`: `BODS_API_KEY`, `NTA_API_KEY`. Without them, England still has the public AVL zip; Ireland stays empty.

## What we will not claim

- National NTA coverage
- Europe-wide punctuality index
- Live-to-the-second ops
- Wave 8 “Done” as a CitySwift clone
