---
paths:
  - "src/aequitas/ingestion/**"
  - "src/aequitas/processing/**"
  - "src/aequitas/validation/**"
  - "src/aequitas/core/models.py"
---

# Data Quality Rules — Non-Negotiable

## Socio-Economic Factors (9 — all must be in master_lsoa_table before pipeline)
1. Deprivation (IMD score/decile) ✅
2. Unemployment rate (TS066) ✅
3. Car ownership % no-car (TS045) ✅
4. Elderly population % aged 65+ (TS007a) ✅
5. Income levels (IMD income sub-domain) ✅
6. Ethnic composition (TS021) ✅
7. Gender-adjusted accessibility proxy ✅
8. Urban/rural classification (RUC 2021) ✅
9. Disability / long-term health conditions (TS038) ✅

## Entity Counting (critical)
- A BusStop = one physical location, identified by ATCO code, counted ONCE
- A Route = one named service, identified by route_id, counted ONCE regardless of regions or journey patterns
- NaPTAN: filter StopType to BCT/BCS/BCE only — rail/tram/ferry/taxi stops must be excluded
- BODS: count routes not journey patterns — one route has many daily patterns
- Cross-region deduplication is mandatory — same route in 2 regional feeds = 1 route

## Known Data Traps
- IMD 2025 uses 2021 LSOA boundaries — 33,755 rows, zero mismatch with Census 2021 (IMD 2019 is obsolete, do not use)
- NOMIS TS066 unemployment is confirmed LSOA-level (0 nulls, range 0–27.1%) — no MSOA distribution needed
- NaPTAN covers all UK transport modes — must filter to England bus stops only (BCT/BCS/BCE, Status=active, ATCO 0xx-4xx)
- ONS Census LSOA population sum must equal official regional total — confirmed 56,490,056 for England
- BODS stop_times.txt is 5.8 GB — read in chunks, never load fully into memory
- NaPTAN Status field uses value `'active'` not `'act'` — confirmed in audit (act=0 rows, active=387,377 rows)
- KDTree index alignment: always reset_index(drop=True) after filtering NaPTAN before building tree
- NHS ODS ORD API: Offset must start at 1 (not 0). Use `Next-Page` response header for pagination, not manual offset. RO198=hospitals, RO177=GPs.
- NOMIS BRES: LSOA level suppressed. Use MSOA (TYPE297) with date=2023 (2024 shows "missing"). employment_status=1 for Employees.
- GIAS schools: file encoding is latin-1, not utf-8. Easting/Northing present for 97.8% of records.
- BODS shapes.txt: shape_dist_traveled is 100% null — always compute route lengths via Haversine from coordinates.
- BODS trips.txt: 48.5% of trips lack shape_id — routes without geometry are flagged has_geometry=False, not dropped.
- lsoa_service_levels.parquet (from 02g): total_weekday_trips is zero-filled (skeleton output). Authoritative weekday trip counts are in lsoa_service_quality.parquet → total_weekday_departures.
- ONS boundary files: regions GeoJSON uses 2022 vintage columns (RGN22CD/RGN22NM), not RGN21. Always detect column names dynamically.
- np.trapz removed in NumPy 2.x — use np.trapezoid with hasattr guard for Gini calculations.

## Validation Gates
- Every ingestion step must write a validation report before the next step starts
- Match rates for all spatial joins must be logged (stop→LSOA, LSOA→demographics)
- Any match rate below 95% must raise a warning and halt unless explicitly overridden
- Ground truth counts (established in data audit notebook) must be checked at pipeline end
