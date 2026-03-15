# Aequitas — Data Downloads Reference

Tracks all datasets needed for Phase 0 EDA. Use the Gemini prompts below to get exact, current download URLs.
Update the status column when a file is downloaded to `data/raw/`.

---

## Status Summary

| Dataset | Purpose | Status | Local Path |
|---------|---------|--------|------------|
| NaPTAN | Bus stop locations | ✅ Downloaded | `data/raw/naptan/Stops.csv` |
| BODS GTFS | Routes, trips, shapes, stop_times | ✅ Downloaded | `data/raw/bods/bods_gtfs_all.zip` |
| ONS Census TS001 | Population | ✅ Downloaded | `data/raw/census/` |
| ONS Census TS007a | Age structure | ✅ Downloaded | `data/raw/census/` |
| ONS Census TS021 | Ethnicity | ✅ Downloaded | `data/raw/census/` |
| ONS Census TS045 | Car ownership | ✅ Downloaded | `data/raw/census/` |
| ONS Census TS066 | Unemployment (LSOA) | ✅ Downloaded | `data/raw/nomis/` |
| IMD 2025 | Deprivation scores | ✅ Downloaded | `data/raw/imd/imd2025_all_ranks_scores_deciles.csv` |
| RUC 2021 | Rural/urban classification | ✅ Downloaded | `data/raw/census/ruc2021_lsoa_ew.csv` |
| LSOA boundaries GeoJSON | Spatial joins | ✅ Downloaded | `data/raw/boundaries/` |
| **Census TS038** | Disability / long-term health | ✅ Downloaded | `data/raw/census/census2021-ts038-lsoa.csv` |
| **DESNZ GHG factors 2025** | Carbon / modal shift | ✅ Downloaded | `data/raw/carbon/ghg-conversion-factors-2025-condensed-set.xlsx` |
| **Code-Point Open** | Postcode → Easting/Northing (replaces ONSPD for NHS ODS geocoding) | ✅ Downloaded | `data/raw/boundaries/code_point_open/data/CSV/` |
| **TAG Databook v2.03fc** | BCR / time values (Dec 2025, May 2026 changes) | ✅ Downloaded | `data/raw/tag/tag-data-book-v2-03fc-dec-2025.xlsm` |
| **NHS ODS hospitals** | Healthcare accessibility | ✅ Downloaded | `data/raw/poi/hospitals.csv` |
| **NHS ODS GP surgeries** | Healthcare accessibility | ✅ Downloaded | `data/raw/poi/epraccur.csv` |
| **GIAS links** | School predecessor relationships (not needed for EDA) | ✅ Downloaded | `data/raw/poi/gias_links.csv` |
| **GIAS schools** | Education accessibility | ✅ Downloaded | `data/raw/poi/gias_schools.csv` (61MB, 52,278 rows, 27,183 open, 3,173 secondary) |
| **NOMIS BRES (MSOA, 2023)** | Employment centre proxy | ✅ Downloaded | `data/raw/nomis/bres_msoa_2023.csv` |

---

## Gemini Prompts for Download Links

Run each prompt in Gemini to get the exact, current download URL. Do not guess URLs.

---

### 1. Census TS038 — Disability / Long-term Health Conditions

**Used for:** Factor 9 (disability) in vulnerability index. Disabled people are disproportionately transit-dependent — omitting this is a gap policy reviewers will flag.

**Save to:** `data/raw/census/census2021-ts038-lsoa.csv` (extract from ZIP)

**Download URL (verified):**
```
https://www.nomisweb.co.uk/output/census/2021/census2021-ts038.zip
```
Extract `census2021-ts038-lsoa.csv` from the ZIP. Contains England + Wales LSOAs — filter to England only on load (same pattern as other Census tables).

**Alternative (England-only CSV):** ONS TS038 dataset page → Filter and download → Area Type: Lower layer Super Output Areas → Coverage: England → Get data.

---

### 2. NHS ODS — Hospital Locations

**Status: ✅ Downloaded** — `data/raw/poi/hospitals.csv` (3,870 England acute sites)

**Used for:** Healthcare accessibility gap analysis. Which deprived LSOAs have no bus route to a hospital?

**Downloaded via ORD 2-0-0 API (automated):**
```
https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations?PrimaryRoleId=RO198&Status=Active&Limit=1000&Offset=1
```
- Role: RO198 = NHS Trust Site. Paginate using `Next-Page` response header.
- Total active: 38,217. Filtered to England postcodes + name contains HOSPITAL/INFIRMARY = 3,870 acute sites.
- CSV columns: OrgId, Name, PostCode, LastChangeDate
- Postcodes only — join to Code-Point Open for Easting/Northing coordinates.

**Note:** Legacy bulk ZIPs (`files.digital.nhs.uk`) are CloudFront-blocked since 2026. ORD 2-0-0 API is the only open-access automated method.

---

### 3. NHS ODS — GP Surgery Locations

**Status: ✅ Downloaded** — `data/raw/poi/epraccur.csv` (12,213 England practices)

**Used for:** Healthcare accessibility gap analysis. Primary care access is the most policy-relevant healthcare metric at LSOA level.

**Downloaded via ORD 2-0-0 API (automated):**
```
https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations?PrimaryRoleId=RO177&Status=Active&Limit=1000&Offset=1
```
- Role: RO177 = Prescribing Cost Centre (GP practices). Same pagination approach.
- Total active: 12,858. Filtered to England postcodes = 12,213.
- CSV columns: OrgId, Name, PostCode, LastChangeDate
- Postcodes only — join to Code-Point Open for coordinates.

---

### 4. GIAS — State School Locations

**Used for:** Education accessibility analysis. Which deprived LSOAs have no bus route to a secondary school?

**Save to:** `data/raw/poi/gias_schools.csv`

**Download (no static URL — regenerated daily):**
```
https://get-information-schools.service.gov.uk/Downloads
```
Go to portal → Establishment data section → Download establishment data → CSV named `edubasealldataYYYYMMDD.csv`.

**Filters to apply on load:**
- `EstablishmentStatus` = Open
- `PhaseOfEducation` = Secondary (for secondary school gap analysis)

---

### 5. TAG Databook v2.03fc — DfT Time Values

**Status: ✅ Downloaded** — `data/raw/tag/tag-data-book-v2-03fc-dec-2025.xlsm`

**Note:** Downloaded version is v2.03fc (Dec 2025, includes changes for May 2026) — this is newer and supersedes v2.02. `.xlsm` format. Scraped URL:
```
https://assets.publishing.service.gov.uk/media/694a908c888ddc41b48a54f9/tag-data-book-v2-03fc-dec-2025.xlsm
```

**TODO:** Open file, extract current values from tabs `A1.3.1`, `A1.3.2` (Value of Time) and `A1.3.7` (Vehicle Operating Costs), then:
- Update TAG constants table in `memory/architecture.md`
- Update all ⚠️ Stale TAG-001 through TAG-005 entries in `docs/figures-registry.md` to ✅ Confirmed

---

### 6. DESNZ GHG Conversion Factors 2025

**Used for:** Carbon reduction from modal shift. Bus + car CO₂ per passenger-km. Published June 2025 — significantly updated from 2022 (greener grid, updated occupancy rates).

**Save to:** `data/raw/carbon/ghg-conversion-factors-2025-condensed-set.xlsx`

**Direct Download URLs (verified):**
```
Condensed set (sufficient for transport factors):
https://assets.publishing.service.gov.uk/media/6846a4e6d25e6f6afd4c0180/ghg-conversion-factors-2025-condensed-set.xlsx

Full set (if needed):
https://assets.publishing.service.gov.uk/media/6846a4f55e92539572806125/ghg-conversion-factors-2025-full-set.xlsx
```

**After downloading:** Update CO2-001 and CO2-002 in `docs/figures-registry.md` to ✅ Confirmed with new values.

---

### 7. NOMIS BRES — Business / Employment Counts

**Status: ✅ Downloaded (MSOA level, 2023)**

LSOA level suppressed for disclosure control (both `NM_189_1` BRES and `NM_2002_1` Business Counts return empty for `TYPE298`). Also 2024 data shows "figures are missing" — latest available is 2023.

**Downloaded via:**
```
https://www.nomisweb.co.uk/api/v01/dataset/NM_189_1.data.csv?geography=TYPE297&date=2023&industry=37748736&employment_status=1&measure=1&measures=20100&select=GEOGRAPHY_CODE,GEOGRAPHY_NAME,OBS_VALUE
```
- `TYPE297` = MSOA, `date=2023`, `employment_status=1` (Employees)
- 6,791 England MSOAs, 0 nulls, 27.3M total employees
- Saved to `data/raw/nomis/bres_msoa_2023.csv`
- Spatially join MSOAs to LSOAs for employment centre proxy

---

## Postcode → Coordinates: Code-Point Open (replaces ONSPD)

**Status: ✅ Downloaded** — `data/raw/boundaries/code_point_open/data/CSV/` (one CSV per postcode area prefix)

OS Code-Point Open (Feb 2026, free, no auth required) provides all GB postcodes with Easting/Northing in British National Grid. Lighter and more maintainable than ONSPD.

Downloaded via OS Downloads API:
```
https://api.os.uk/downloads/v1/products/CodePointOpen/downloads?area=GB&format=CSV&redirect
```

**Usage:** Join NHS ODS and GIAS files on postcode column → get Easting/Northing → convert to WGS84 lat/lon for spatial analysis.

---

## Notes on Processing After Download

- NHS ODS (hospitals + GP surgeries): Downloaded via ORD 2-0-0 API (automated, no browser required). Uses `Next-Page` response header for pagination, `X-Total-Count` for total. Role IDs: RO198 = NHS Trust Site (hospitals), RO177 = Prescribing Cost Centre (GP practices). Files filtered to England only and saved with headers: `OrgId, Name, PostCode, LastChangeDate`. hospitals.csv = 3,870 acute sites (name contains HOSPITAL/INFIRMARY). epraccur.csv = 12,213 GP practices. Join postcodes to Code-Point Open for coordinates.
- GIAS schools: manual browser download from `get-information-schools.service.gov.uk/Downloads`. Filter `EstablishmentStatus=Open`, `PhaseOfEducation=Secondary`.
- TAG v2.03fc: open `data/raw/tag/tag-data-book-v2-03fc-dec-2025.xlsm`, extract values from tabs A1.3.1, A1.3.2, A1.3.7, update `memory/architecture.md` and `docs/figures-registry.md`.
- DESNZ 2025: open `data/raw/carbon/ghg-conversion-factors-2025-condensed-set.xlsx`, extract transport factors, update figures-registry.md CO2-001 and CO2-002.
- TS038: joins to master_lsoa_table on LSOA code. Filter to England only on load (file contains England + Wales).
- NOMIS BRES: LSOA level suppressed. Downloaded MSOA level (2023, date=2023, employment_status=1). 6,791 England MSOAs, 0 nulls, 27.3M total employees. Spatially join MSOAs to LSOAs to create employment proxy. Note: 2024 data shows "missing" — use 2023 as latest available.
