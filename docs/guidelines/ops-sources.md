# Wave 8 ops — source log

Fetched **2026-08-17**, England re-checked **2026-09-25** (no `BODS_API_KEY`). Only URLs actually hit. Status and bytes are measured.
No invented second URL. No paid Swiftly / CitySwift / Google. Rollups live in
`data/ops/{country}/latest.json` (gitignored). Static DuckDB files were not written.

Late threshold used when `delay` is present: **> 300 seconds (5 minutes)**.
A snapshot is not “live to the second.”

## England — BODS (OGL)

| URL | Entity | Auth | HTTP | Bytes | Notes |
|-----|--------|------|------|------:|-------|
| `https://data.bus-data.dft.gov.uk/api/v1/gtfsrtdatafeed/` | TripUpdates + VehiclePositions API | none (`BODS_API_KEY` unset) | **401** | 6 | Do not invent a second path |
| `https://data.bus-data.dft.gov.uk/api/v1/datafeed/` | SIRI-VM API | none | **401** | 6 | Same key gate |
| `https://data.bus-data.dft.gov.uk/avl/download/gtfsrt` | GTFS-RT zip (AVL download) | none | **200** (302 → signed `download.bus-data.dft.gov.uk`) | **1,935,686** | VehiclePositions-style feed. 2026-09-25 |

**Rollup (2026-09-25, key unset):** `n_updates=29391`, `n_with_delay=0`, `pct_late` null, `n_routes_with_update=6254` of **13640** static warehouse routes → **coverage 45.85%**. TripUpdates and SIRI-VM still **401** / 6 bytes. **Not** a DfT punctuality statistic. Prior 2026-08-17 AVL run was 5,351 of 13,640 with the same `n_with_delay=0`.

Collector policy: optional `BODS_API_KEY` (env only, never committed). If TripUpdates or SIRI-VM returns a `delay` field, `pct_late` is the share with delay **> 300 seconds**. If the key is unset, or the authenticated feed still has no delay, keep the public AVL zip, leave late as **—**, and say `n_with_delay = 0`. SIRI-VM contributes only when a `Delay` element is present — clocks are not turned into delay. Stop → LSOA uses the existing England warehouse only. Score stays **80.0**.

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
