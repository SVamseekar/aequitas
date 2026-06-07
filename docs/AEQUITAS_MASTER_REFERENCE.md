# Aequitas Platform — Master Reference Document
## Part 1 of 3: Platform Overview, Data Pipeline & Backend Packages

---

## 1. PLATFORM OVERVIEW

### What is Aequitas?

Aequitas is a UK bus transport policy intelligence platform. Policy makers at the Department for Transport (DfT) and Local Transport Authorities (LTAs) use it to analyse how bus coverage correlates with socioeconomic deprivation across every Lower Super Output Area (LSOA) in England. The platform combines a pre-computed analytics dashboard with a Gemini-powered RAG chatbot for natural language Q&A.

### Business Capabilities

| Capability                                            | Channel            | Status |
| ----------------------------------------------------- | ------------------ | ------ |
| Equity & deprivation analytics (Gini, Palma, CI)      | Web dashboard      | Live   |
| Accessibility analysis (2SFCA, 400m coverage)         | Web dashboard      | Live   |
| Service quality index per LSOA                        | Web dashboard      | Live   |
| Route network & operator concentration (HHI)          | Web dashboard      | Live   |
| Socioeconomic correlations (RF, SHAP)                 | Web dashboard      | Live   |
| Economic appraisal (BCR, TAG Green Book)              | Web dashboard      | Live   |
| Bus Services Act 2025 readiness                       | Web dashboard      | Live   |
| Policy scenario modelling (DRT, frequency, franchise) | Web dashboard      | Live   |
| RAG chatbot over policy narratives                    | Web (chat drawer)  | Live   |
| PDF export per dimension                              | Web                | Live   |
| Conversation persistence (Supabase)                   | Web (chat sidebar) | Live   |
| Saved analyses, policy notes, watchlist regions       | Web                | Live   |

### Policy Dimensions (8 — all pre-computed)

| ID               | Dimension                 | Key Metric              |
| ---------------- | ------------------------- | ----------------------- |
| equity           | Equity & Deprivation      | Gini coefficient 0.5741 |
| accessibility    | Accessibility             | 400m stop coverage %    |
| service_quality  | Service Quality           | SQI mean 65.4/100       |
| route_network    | Route Network             | Operator HHI            |
| correlations     | Socio-Economic & ML       | Deprivation Pearson r   |
| economic         | Economic Appraisal        | CO₂ saving (tonnes)     |
| bus_services_act | Bus Services Act 2025     | LTA readiness score     |
| scenarios        | Policy Scenario Modelling | Population affected     |

### Ground Truth (Phase 0 — locked, do not change without re-running audit)

| Entity                             | Count                    | Source                                            |
| ---------------------------------- | ------------------------ | ------------------------------------------------- |
| England active bus stops           | 274,719                  | NaPTAN (BCT/BCS/BCE, Status=active, ATCO 0xx-4xx) |
| BODS unique routes                 | 13,099                   | BODS GTFS (9 feeds, deduplicated)                 |
| BODS total trips                   | 1,752,443                | BODS GTFS                                         |
| Census 2021 England LSOAs          | 33,755                   | ONS Census                                        |
| Census population (England)        | 56,490,056               | ONS TS001                                         |
| IMD 2025 LSOAs                     | 33,755                   | MHCLG (zero mismatch)                             |
| LSOAs with zero bus stops          | 4,245                    | Spatial join                                      |
| GIAS open schools (England)        | 27,183                   | 03d                                               |
| Secondary + all-through schools    | 3,336                    | 03d                                               |
| BRES England MSOAs                 | 6,791                    | 03e                                               |
| England employees (BRES 2023)      | 27,343,200               | 03e                                               |
| Code-Point Open England postcodes  | 1,492,016                | 03h                                               |
| NHS hospitals (geocoded)           | 3,714                    | 03b                                               |
| NHS GP practices (geocoded)        | 12,059                   | 03c                                               |
| Routes with geometry               | 7,241 (53.1%)            | 04a                                               |
| Mean route length                  | 23.0 km (median 18.7 km) | 04a                                               |
| Cross-LA routes                    | 5,143 (37.7%)            | 04a                                               |
| Evening isolated LSOAs             | 5,189 (15.4%)            | 04b                                               |
| Sunday desert LSOAs                | 6,745 (20.0%)            | 04b                                               |
| Mean SQI                           | 65.4/100                 | 04b                                               |
| Gini coefficient (bus service)     | 0.5741                   | 04c                                               |
| Palma ratio                        | 5.702                    | 04c                                               |
| Concentration Index (trips vs IMD) | +0.1358 PRO-RICH         | 04c                                               |
| Triple-deprived LSOAs              | 612 (1.8%)               | 04c                                               |
| RF coverage prediction R²          | 0.472                    | 04d                                               |
| Top SHAP feature                   | nocar_pct                | 04d                                               |
| Bus CO₂ (avg local, DESNZ 2025)    | 0.10385 kg/pax-km        | 03g                                               |
| Car CO₂ (avg diesel, DESNZ 2025)   | 0.17304 kg/veh-km        | 03g                                               |

---

## 2. INFRASTRUCTURE

### Stack

| Layer               | Technology                               | Version             |
| ------------------- | ---------------------------------------- | ------------------- |
| Backend             | FastAPI + uvicorn[standard]              | 0.115+ / 0.32+      |
| Language            | Python                                   | 3.12+               |
| Data warehouse      | DuckDB (read-only, pre-built)            | 1.1+                |
| Pipeline ORM        | pandas + geopandas                       | 2.2+ / 1.0+         |
| ML                  | scikit-learn, HDBSCAN, SHAP              | 1.5+ / 0.8+ / 0.45+ |
| LLM                 | Gemini 2.5 Flash (google-genai)          | 1.68+               |
| Vector store        | FAISS (faiss-cpu, in-memory)             | 1.8+                |
| Embeddings          | all-MiniLM-L6-v2 (sentence-transformers) | 3.3+                |
| Frontend            | React + Vite + TypeScript                | 19 / 6 / 5.9        |
| UI library          | shadcn/ui + Tailwind CSS                 | v4                  |
| Charts              | Observable Plot                          | 0.6+                |
| Auth / persistence  | Supabase (Postgres + RLS)                | JS v2               |
| PDF export          | ReportLab                                | 4.4+                |
| Narrative templates | Jinja2                                   | 3.1+                |
| CLI                 | Click                                    | 8.1+                |
| Logging             | loguru                                   | 0.7+                |
| Validation          | Pydantic v2                              | 2.6+                |

### Build Phases

| Phase   | Name                                        | Status                  |
| ------- | ------------------------------------------- | ----------------------- |
| Phase 0 | Data Audit + EDA (19 notebooks, 103 checks) | ✅ COMPLETE (2026-03-14) |
| Phase 1 | Pipeline + Warehouse                        | ✅ COMPLETE              |
| Phase 2 | Frontend + RAG chatbot                      | ✅ COMPLETE              |
| Phase 3 | Deploy + CI/CD                              | ⏳ Not started           |

### Service Ports (local dev)

| Service         | Port | Technology      |
| --------------- | ---- | --------------- |
| FastAPI backend | 8000 | uvicorn         |
| React frontend  | 5173 | Vite dev server |

### Data Directories

| Directory                  | Contents                                                           |
| -------------------------- | ------------------------------------------------------------------ |
| `data/raw/`                | Raw government data (NaPTAN, BODS, Census, IMD, etc.) — gitignored |
| `data/audit/`              | Phase 0 Parquet + JSON outputs — ground truth source               |
| `data/processed/`          | Pipeline stage outputs — gitignored                                |
| `data/aequitas.duckdb`     | Pre-built warehouse — gitignored                                   |
| `data/faiss_index.bin`     | FAISS embeddings index — gitignored                                |
| `data/faiss_metadata.json` | Per-chunk section metadata — gitignored                            |

### Environment Variables

| Variable                        | Required       | Purpose                                                    |
| ------------------------------- | -------------- | ---------------------------------------------------------- |
| `GEMINI_API_KEY`                | YES            | Gemini 2.5 Flash for RAG chat                              |
| `SUPABASE_URL`                  | YES            | Supabase project URL                                       |
| `SUPABASE_SERVICE_ROLE_KEY`     | YES            | Backend Supabase admin client                              |
| `SUPABASE_JWT_SECRET`           | YES (prod)     | JWT validation (HS256)                                     |
| `AEQUITAS_DB_PATH`              | No             | DuckDB path (default: `data/aequitas.duckdb`)              |
| `AEQUITAS_FAISS_INDEX`          | No             | FAISS index path (default: `data/faiss_index.bin`)         |
| `AEQUITAS_FAISS_METADATA`       | No             | Metadata path (default: `data/faiss_metadata.json`)        |
| `AEQUITAS_CORS_ORIGINS`         | No             | Comma-separated origins (default: `http://localhost:5173`) |
| `ENVIRONMENT`                   | No             | `development` or `production`                              |
| `DEV_AUTH_BYPASS`               | No             | `true` to skip JWT in dev (NEVER in production)            |
| `VITE_SUPABASE_URL`             | YES (frontend) | Supabase URL for browser client                            |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | YES (frontend) | Supabase anon key                                          |

---

## 3. CORE PACKAGE (`src/aequitas/core/`)

**Python Files:** 5

### 3.1 Configuration (`config.py`)

`PipelineConfig` dataclass — single source of truth for all pipeline paths and thresholds.

```
project_root      Path    — repo root (auto-detected from __file__)
raw_dir           Path    — data/raw/
audit_dir         Path    — data/audit/
processed_dir     Path    — data/processed/
warehouse_path    Path    — data/aequitas.duckdb
min_match_rate    float   — 0.95 (spatial join minimum)
stops_per_1000_max float  — 30.0 (sanity cap — prevents stop-route double counting)
routes_sanity_max int     — 50,000
stop_times_chunk_size int — 1,000,000 (BODS 5.8GB streaming)
shapes_chunk_size int     — 500,000
faiss_index_path  Path    — data/faiss_index.bin
faiss_metadata_path Path  — data/faiss_metadata.json
gemini_api_key    str     — from GEMINI_API_KEY env
api_cors_origins  list    — from AEQUITAS_CORS_ORIGINS env
```

`filter_combinations()` → list of all 30 `(region, urban_rural)` tuples (10 regions × 3 area types).

### 3.2 Constants (`constants.py`)

Two lazy singletons — call as `TAG()` and `DESNZ()`. Loaded once from Phase 0 audit JSON files, cached with `@functools.cache`.

**Population denominator (hardcoded — never change without re-running audit):**
```python
POPULATION_ENGLAND: int = 56_490_056
LSOA_COUNT_ENGLAND: int = 33_755
```

**`TAGConstants` (TAG Databook v2.03fc, Dec 2025):**
```
vot_commuting_2014         float  — Value of Time, commuting, 2014 prices (per hr)
vot_leisure_2014           float  — Value of Time, leisure, 2014 prices
vot_business_avg_2014      float  — Value of Time, business avg, 2014 prices
vot_commuting_2023         float  — A1.3.1 published, 2023 prices (factor cost)
vot_leisure_2023           float
vot_business_avg_2023      float
carbon_value_central_2010  float  — £/tonne CO₂e, central estimate
carbon_value_central_2025  float
carbon_value_central_2030  float
social_discount_rate       float  — 0.035 (3.5% — Green Book)
```

**`DESNZConstants` (GHG Conversion Factors 2025):**
```
bus_co2_avg_local    float  — 0.10385 kg CO₂e/pax-km (average local bus)
bus_co2_not_london   float
bus_co2_london       float
coach_co2            float
car_co2_avg_diesel   float  — 0.17304 kg CO₂e/veh-km
car_co2_per_pax_km   float  — per passenger-km (derived)
rail_co2             float
modal_shift_car_to_bus float — CO₂ saving per pax-km switching car→bus
car_occupancy        float
```

### 3.3 Pydantic v2 Data Models (`models.py`)

Every data boundary uses one of these models. Raw in, validated model out, always.

**`BusStop`** — one physical stop, identified by ATCO code, counted once:
```
stop_id     str   — NaPTAN ATCO code (validated: format + England prefix)
stop_name   str
latitude    float — validated: UK bounding box
longitude   float — validated: UK bounding box
lsoa_code   str   — validated: E01xxxxxx format
region_code str
stop_type   str   — BCT | BCS | BCE
```

**`Route`** — one named service, counted once regardless of journey patterns:
```
route_id         str
line_name        str
route_length_km  float ≥ 0
num_stops        int ≥ 0
trips_per_day    int ≥ 0
regions_served   list[str]
has_geometry     bool
```

**`LSOARecord`** — one LSOA with all 9 socioeconomic factors:
```
lsoa_code           str
lsoa_name           str
population          int > 0
imd_score           float ≥ 0
imd_decile          int 1–10
unemployment_rate   float 0–100
nocar_pct           float 0–100
elderly_pct         float 0–100
income_score        float 0–1
nonwhite_pct        float 0–100
geo_barriers_score  float ≥ 0
urban_rural         str
disability_pct      float 0–100
```

**`RegionSummary`** — per-region aggregated statistics:
```
region_code       str
region_name       str
population        int > 0
unique_stops      int ≥ 0
unique_routes     int ≥ 0
stops_per_1000    float ≥ 0   — validator rejects > 30 (data trap guard)
routes_per_100k   float ≥ 0
```

**`SectionResult`** — one pre-computed (region × urban_rural × section) row:
```
region      str
urban_rural str
section_id  str
stats       dict
chart_data  dict
narrative   str
```

**`ProvenanceEntry`** — audit trail for one metric:
```
metric_id    str
value        float
formula      str
inputs       dict
source_files list[str]
```

### 3.4 Types (`types.py`)

```python
class RegionCode(str, Enum):
    NORTH_EAST     = "E12000001"
    NORTH_WEST     = "E12000002"
    YORKSHIRE      = "E12000003"
    EAST_MIDLANDS  = "E12000004"
    WEST_MIDLANDS  = "E12000005"
    EAST_OF_ENGLAND = "E12000006"
    LONDON         = "E12000007"
    SOUTH_EAST     = "E12000008"
    SOUTH_WEST     = "E12000009"

class StopType(str, Enum):
    BCT = "BCT"   # On-street Bus/Coach/Tram stop (most common)
    BCS = "BCS"   # Bus/Coach station bay
    BCE = "BCE"   # Bus/Coach station entrance

class UrbanRural(str, Enum):
    URBAN = "urban"
    RURAL = "rural"

class IMDDecile(IntEnum):
    D1–D10        # 1 = most deprived, 10 = least deprived

ENGLAND_ATCO_PREFIXES: frozenset[str]   # "000" to "499"
```

### 3.5 Validators (`validators.py`)

```
validate_atco_code(v)     — ATCO format + England prefix 000–499
validate_lsoa_code(v)     — E01xxxxxx format
validate_uk_latitude(v)   — bounding box 49.8–55.9
validate_uk_longitude(v)  — bounding box -6.5–1.9
```

---

## 4. PIPELINE CLI (`src/aequitas/pipeline/`)

**Python Files:** 2

### Commands (`cli.py`)

Entry point: `aequitas` (registered in `pyproject.toml`).

| Command                 | Stage | Purpose                                            |
| ----------------------- | ----- | -------------------------------------------------- |
| `aequitas ingest`       | 1     | Load + filter raw data sources → Parquet           |
| `aequitas process`      | 2     | Spatial joins, dedup, demographics, geometry, SQI  |
| `aequitas analytics`    | 3     | Equity, ML, accessibility, economic, policy        |
| `aequitas intelligence` | 4     | InsightEngine — generate evidence-gated narratives |
| `aequitas warehouse`    | 5     | Build DuckDB from Parquet + narratives             |
| `aequitas validate`     | 6     | Ground truth validation gates                      |
| `aequitas rag`          | 7     | Build FAISS index from DuckDB narratives           |
| `aequitas run`          | all   | Run all 7 stages end-to-end                        |

### Stage Orchestration (`_stages.py`)

`StageReport` dataclass returned by every stage:
```
stage          str
duration_s     float
output_files   list[Path]
checks_passed  int
checks_failed  int
```

**Stage 1 — Ingestion:** NaPTAN (274,719 stop check), BODS routes, master LSOA table (33,755 row check). Raises on failure — never silently continues.

**Stage 2 — Processing:** Route geometries (Haversine — shape_dist_traveled is 100% null in BODS), service quality (fast path: Phase 0 `stop_headways.parquet`; slow path: stream 5.8GB `stop_times.txt`).

**Stage 3 — Analytics:** In current implementation, verifies Phase 0 audit Parquets exist. Full re-computation requires Stage 2 outputs. Analytics modules are separately callable.

**Stage 4 — Intelligence:** Runs `precompute_all_sections()`, stashes results on `cfg._section_results` for Stage 5 handoff.

**Stage 5 — Warehouse:** Calls `build_warehouse()`. If run standalone (without Stage 4 in the same process), re-runs precompute. Writes `CHECKPOINT` at end.

**Stage 6 — Validation:** Compares Parquet outputs against `data/audit/ground_truth.json`. Logs PASS/WARN/FAIL per check.

**Stage 7 — RAG Index:** Builds FAISS index from DuckDB narratives, saves `faiss_index.bin` + `faiss_metadata.json`.

---

## 5. INGESTION PACKAGE (`src/aequitas/ingestion/`)

**Python Files:** 8

### 5.1 NaPTAN Bus Stops (`naptan.py`)

**Filter chain (must be applied in this exact order):**
1. `StopType ∈ {BCT, BCS, BCE}` — excludes rail, tram, ferry, taxi
2. `Status == 'active'` — Note: value is `'active'` not `'act'`
3. `ATCOCode[0] ∈ {'0','1','2','3','4'}` — England only (5+ = Scotland/Wales/NI)
4. Drop rows where `Latitude` or `Longitude` is null
5. `drop_duplicates(subset='ATCOCode')` + `reset_index(drop=True)`

**Ground truth output:** 274,719 rows.

**Critical:** `reset_index(drop=True)` after filtering is required before building KDTree for spatial join — index alignment would otherwise be broken.

### 5.2 BODS GTFS (`bods.py`)

Reads from bulk GTFS zip archive. Heavy files (`stop_times.txt` 5.8GB, `shapes.txt` 3.2GB) are NOT loaded here — streamed in processing.

| Function                       | GTFS file      | Ground truth            |
| ------------------------------ | -------------- | ----------------------- |
| `load_bods_routes(zip_path)`   | `routes.txt`   | 13,099 unique route_ids |
| `load_bods_trips(zip_path)`    | `trips.txt`    | 1,752,443 trips         |
| `load_bods_stops(zip_path)`    | `stops.txt`    | 310,598 unique stop_ids |
| `load_bods_calendar(zip_path)` | `calendar.txt` | —                       |

**Critical data traps:**
- Count **routes** not journey patterns — one route has many daily patterns
- Cross-region deduplication is mandatory — same route in 2 regional feeds = 1 route
- 48.5% of trips lack `shape_id` — flag `has_geometry=False`, never drop these trips
- `shape_dist_traveled` in `shapes.txt` is 100% null — compute lengths via Haversine

### 5.3 Other Ingestion Modules

| Module                | Source                    | Key Notes                                                     |
| --------------------- | ------------------------- | ------------------------------------------------------------- |
| `census.py`           | ONS Census 2021           | Population denominator must equal 56,490,056                  |
| `imd.py`              | MHCLG IMD 2025            | 33,755 LSOAs, zero mismatch with Census 2021                  |
| `boundaries.py`       | ONS LSOA boundaries       | 2022 vintage — detect `RGN22CD`/`RGN22NM` columns dynamically |
| `poi.py`              | NHS ODS, GIAS, NOMIS BRES | See data traps below                                          |
| `ruc.py`              | ONS RUC 2021              | Binary collapse: urban/rural                                  |
| `constants_loader.py` | Phase 0 JSON outputs      | Loads `tag_constants.json`, `desnz_carbon_factors.json`       |

**POI data traps:**
- GIAS schools: encoding is `latin-1`, not `utf-8`
- NHS ODS API: offset starts at 1 (not 0); use `Next-Page` header for pagination — RO198=hospitals, RO177=GPs
- NOMIS BRES: LSOA level suppressed — use MSOA (TYPE297), `date=2023`, `employment_status=1`
- ONS boundaries: regions GeoJSON uses 2022 vintage columns — detect dynamically, never hardcode `RGN21CD`

---

## 6. PROCESSING PACKAGE (`src/aequitas/processing/`)

**Python Files:** 5

### 6.1 Service Quality (`service_quality.py`)

**Two execution paths:**
- **Fast path (seconds):** Loads Phase 0 `data/audit/stop_headways.parquet` if it exists
- **Full path (~90 min):** Streams `stop_times.txt` in 1M-row chunks from raw BODS GTFS zip

**Time band thresholds (minutes from midnight — matches Phase 0 notebook 04b exactly):**
```
AM peak:      07:00–09:30
Interpeak:    09:30–16:00
PM peak:      16:00–18:30
Evening:      ≥ 18:30
Evening isolated threshold:   last service before 19:00
Night isolated threshold:     last service before 22:00
```

**Day-type priority ordering (weekday > saturday > sunday):** A trip running Mon–Sun is classified as 'weekday', not multi-labelled.

**Service Quality Index (SQI) — composite 0–100:**
```
SQI = 0.40 × headway_score
    + 0.20 × span_score
    + 0.20 × frequency_score
    + 0.10 × evening_score
    + 0.10 × sunday_score
```

Where:
- `headway_score` = `(100 - (mean_headway_min / 60) * 100).clip(0, 100)` — 0 for no service
- `span_score` = `((last - first) / (18*60) * 100).clip(0, 100)`
- `frequency_score` = `(total_weekday_departures / 100 * 100).clip(0, 100)`
- `evening_score` = `((last_dep - 18*60) / (4*60) * 100).clip(0, 100)` — 0 for no service
- `sunday_score` = `(sunday_trips / weekday_trips * 200).clip(0, 100)` — 0 when no weekday service

**Critical:** `lsoa_service_levels.parquet` (from notebook 02g) has `total_weekday_trips` zero-filled. Always use `lsoa_service_quality.parquet → total_weekday_departures`.

**Ground truth validation:**
- Evening isolated LSOAs: 5,189
- Sunday desert LSOAs: 6,745
- Mean SQI: 65.4

### 6.2 Route Geometry (`route_geometry.py`)

Computes route lengths via Haversine from BODS `shapes.txt` coordinates. `shape_dist_traveled` is 100% null and must never be used.

**Ground truth validation:**
- Routes with geometry: 7,241 (53.1%)
- Mean route length: 23.0 km, median 18.7 km
- Cross-LA routes: 5,143 (37.7%)

### 6.3 Other Processing Modules

| Module            | Purpose                                                                         |
| ----------------- | ------------------------------------------------------------------------------- |
| `spatial.py`      | NaPTAN stops → LSOA spatial join (KDTree, EPSG:27700), match rate must be ≥ 95% |
| `dedup.py`        | Cross-region BODS route deduplication                                           |
| `demographics.py` | Builds master LSOA table with all 9 socioeconomic factors from Census, IMD, RUC |

---

## 7. ANALYTICS PACKAGE (`src/aequitas/analytics/`)

**Python Files:** 8

### 7.1 Equity Analytics (`equity.py`)

**NumPy 2.x guard (required — `np.trapz` removed in NumPy 2.x):**
```python
_trapezoid = getattr(np, "trapezoid", getattr(np, "trapz", None))
```

**`compute_gini(values, weights) → float`**
Population-weighted Gini via Lorenz curve area method. Sorts by values ascending, computes cumulative population and service shares, inserts origin (0,0), integrates with trapezoid rule.
- Ground truth: 0.5741 (exceeds UK income Gini of 0.36)

**`compute_palma_ratio(values, weights) → float`**
Mean service in top 10% population / mean service in bottom 40% population.
- Ground truth: 5.702

**`compute_concentration_index(service, rank, population) → float`**
Wagstaff CI via covariance method. Positive = service concentrated in richer (lower deprivation rank) areas.
- Ground truth: +0.1358 (PRO-RICH)

**`compute_vulnerability_index(df) → Series`**
5-factor index (0–100): IMD score, no-car %, elderly %, disability %, unemployment rate. Each factor min-max normalised, equal-weighted average.

**`identify_triple_deprived(df) → Series[bool]`**
Flags LSOAs in worst tertile on 3+ dimensions: IMD score, no-car %, elderly %.
- Ground truth: 612 LSOAs (1.8%)

### 7.2 ML Coverage Prediction (`ml_prediction.py`)

**`train_coverage_model(X, y, ...) → (RandomForestRegressor, dict)`**

Configuration:
```
n_estimators=200, max_depth=10, min_samples_leaf=50
target: log1p(trips_per_capita)
test_size=0.2, random_state=42, n_jobs=-1
```

Metrics returned: `r2_train`, `r2_test`, `mae_test`, `rmse_test`, `n_train`, `n_test`.
- Ground truth: R² = 0.472 on 33,755 LSOAs (53-72% of variance is policy-driven)
- Top SHAP feature: `nocar_pct`

**`compute_shap_importance(model, X, max_samples=1000) → DataFrame`**
TreeExplainer on subsampled X (≤1000 rows for speed). Returns `[feature, mean_abs_shap]` sorted descending.

### 7.3 ML Clustering (`ml_clustering.py`)

**LSOA clustering:** HDBSCAN (2 dense clusters, 87.7% noise) + GMM (4 components) for soft membership.

**Route clustering:** HDBSCAN on numeric features — sentence embeddings deferred.

### 7.4 Anomaly Detection (`ml_anomaly.py`)

Isolation Forest + LOF ensemble.
- Ground truth: 1,688 anomalies (5% of LSOAs)

### 7.5 Accessibility (`accessibility.py`)

2SFCA (Two-Step Floating Catchment Area), 400m Euclidean catchment.
- 6,776 LSOAs have zero access to any POI type.

### 7.6 Economic Appraisal (`economic.py`)

**`pv_annuity(annual, rate, years) → float`**
`PV = annual × (1 - (1+r)^-n) / r`

**`compute_bcr(annual_benefit, annual_cost, rate=None, years=60) → float`**
TAG Green Book methodology — 60-year appraisal, 3.5% social discount rate. Rate defaults to `TAG().social_discount_rate`.

**`compute_modal_shift(current_annual_trips, frequency_increase_pct, ...) → dict`**
DfT bus demand elasticity of frequency = 0.55 (default). Returns:
```
new_trips           float  — induced new bus trips
modal_shift_trips   float  — car trips replaced (25% of new trips)
co2_saved_tonnes    float  — annual CO₂ saving from modal shift
vkt_reduction       float  — vehicle-km avoided per year
```
CO₂ formula: `modal_shift_trips × avg_distance × (car_co2_per_pax_km - bus_co2_avg_local)`

**`compute_investment_gap(current, national_median, population, is_urban, ...) → dict`**
Gap trips to reach national median × operating cost per trip (£2.50 default, ×1.2 for urban). Returns `gap_trips`, `annual_cost_gbp`, `above_median`.

### 7.7 Policy Synthesis (`policy_synthesis.py`)

Combines equity, service quality, and accessibility outputs into priority quadrants:
- Q1: High vulnerability, Low access (PRIORITY)
- Q2–Q4: other combinations

### 7.8 SHAP Export (`shap_export.py`)

Exports SHAP values to Parquet for section_results loading.

---

## 8. INTELLIGENCE PACKAGE — InsightEngine (`src/aequitas/intelligence/`)

**Python Files:** 6 + 30 Jinja2 templates

The InsightEngine is deterministic — Jinja2 templates + evidence-gated rules only. No LLM calls here. Suppress > mislead always.

### 8.1 Section Registry (`section_registry.py`)

Single source of truth for all **51 analytical sections**. Maps each `section_id` → `SectionDef(template, chart_type, category, title)`.

| Category                        | Sections  | Chart types                                                                  |
| ------------------------------- | --------- | ---------------------------------------------------------------------------- |
| A — Coverage & Accessibility    | a1–a8     | horizontal_bar, stacked_bar, lorenz_curve, choropleth, shap_bar              |
| B — Service Quality             | b1–b5     | horizontal_bar, grouped_bar, scatter_regression                              |
| C — Route Characteristics       | c1–c7     | box_violin, horizontal_bar, scatter_regression, scatter_clusters, choropleth |
| D — Socio-Economic Correlations | d1–d8     | scatter_regression, scatter_clusters, heatmap, shap_bar                      |
| F — Equity & Social Inclusion   | f1–f6     | lorenz_curve, horizontal_bar, grouped_bar                                    |
| G — ML Insights                 | g1–g5     | scatter_clusters, scatter_regression, shap_bar, grouped_bar                  |
| J — Economic Impact & BCR       | j1–j4     | horizontal_bar                                                               |
| BSA — Bus Services Act 2025     | bsa1–bsa3 | horizontal_bar, stacked_bar                                                  |
| PS — Policy Scenario Modelling  | ps1–ps5   | horizontal_bar, grouped_bar                                                  |

**Full section list:**

| Section ID                  | Title                                 | Chart type         |
| --------------------------- | ------------------------------------- | ------------------ |
| a1_route_density            | Route density by region               | horizontal_bar     |
| a2_stop_density             | Stop density by region                | horizontal_bar     |
| a3_walking_distance         | Population within 400m of a stop      | stacked_bar        |
| a4_coverage_equity          | Equity of coverage within regions     | lorenz_curve       |
| a5_service_deserts          | Service deserts                       | choropleth         |
| a6_urban_rural_gap          | Urban vs rural coverage gap           | grouped_bar        |
| a7_investment_gap           | Investment to reach national average  | horizontal_bar     |
| a8_coverage_prediction      | Coverage prediction from demographics | shap_bar           |
| b1_frequency                | Average frequency by region           | horizontal_bar     |
| b2_operating_hours          | Operating hours                       | grouped_bar        |
| b3_weekend_penalty          | Weekend service penalty               | grouped_bar        |
| b4_route_frequency          | Most/least frequent routes            | horizontal_bar     |
| b5_frequency_deprivation    | Frequency vs deprivation              | scatter_regression |
| c1_route_length             | Route length distribution             | box_violin         |
| c2_stops_per_route          | Stops per route                       | box_violin         |
| c3_operator_hhi             | Operator landscape (HHI)              | horizontal_bar     |
| c4_urban_rural_routes       | Urban vs rural routes                 | grouped_bar        |
| c5_length_vs_frequency      | Route length vs frequency             | scatter_regression |
| c6_route_archetypes         | Route archetypes                      | scatter_clusters   |
| c7_network_topology         | Network topology                      | choropleth         |
| d1_coverage_deprivation     | Coverage vs deprivation               | scatter_regression |
| d2_coverage_unemployment    | Coverage vs unemployment              | scatter_regression |
| d3_coverage_car             | Coverage vs car ownership             | scatter_regression |
| d4_coverage_elderly         | Coverage vs elderly population        | scatter_regression |
| d5_coverage_income          | Coverage vs income                    | scatter_regression |
| d6_transport_poverty        | Transport poverty clusters            | scatter_clusters   |
| d7_deprivation_urban_rural  | Deprivation × urban/rural             | heatmap            |
| d8_feature_importance       | Feature importance                    | shap_bar           |
| f1_gini                     | Gini coefficient                      | lorenz_curve       |
| f2_disparity_ratio          | Disparity by IMD decile               | horizontal_bar     |
| f3_ethnic_access            | Bus access by ethnicity               | grouped_bar        |
| f4_gender_accessibility     | Gender-adjusted accessibility         | horizontal_bar     |
| f5_rural_penalty            | Rural accessibility penalty           | grouped_bar        |
| f6_equitable_regions        | Most equitable regions                | horizontal_bar     |
| g1_route_clusters           | Route clustering                      | scatter_clusters   |
| g2_anomalies                | Anomaly detection                     | scatter_regression |
| g3_coverage_model           | Coverage prediction                   | scatter_regression |
| g4_shap                     | Feature importance (SHAP)             | shap_bar           |
| g5_scenario_model           | Scenario modelling                    | grouped_bar        |
| j1_economic_value           | Economic value per region             | horizontal_bar     |
| j2_bcr                      | BCR for coverage gaps                 | horizontal_bar     |
| j3_carbon                   | Carbon reduction from modal shift     | horizontal_bar     |
| j4_investment_priority      | Regional investment prioritisation    | horizontal_bar     |
| bsa1_franchising_readiness  | LTA franchising readiness             | horizontal_bar     |
| bsa2_operator_concentration | Operator concentration                | horizontal_bar     |
| bsa3_tier_distribution      | Readiness tier distribution           | stacked_bar        |
| ps1_freq_restoration        | Frequency restoration                 | horizontal_bar     |
| ps2_evening_extension       | Evening extension                     | horizontal_bar     |
| ps3_drt_rural               | DRT for rural areas                   | horizontal_bar     |
| ps4_franchise               | Combined franchise                    | horizontal_bar     |
| ps5_scenario_comparison     | Scenario comparison                   | grouped_bar        |

### 8.2 InsightEngine (`engine.py`)

Maps section IDs to Jinja2 templates and generates narratives. Jinja2 environment: `autoescape` disabled for `.j2` (policy text, not HTML), `trim_blocks=True`, `lstrip_blocks=True`. Custom filter: `format_thousands`.

**Suppression rules:**
- No template registered for section_id → suppress
- `stats` dict is empty → suppress (never render empty template)
- `coverage_density` with subset scope and no ranking data → suppress

**`generate(section_id, region, urban_rural, stats) → dict`**
Returns: `{narrative, section_id, scope, suppressed}`.

**Filter space — 30 combinations:**
- 10 regions: "all" + 9 ONS region codes
- 3 area types: "all", "urban", "rural"
- Skip: single region + non-"all" area type (low-value subsets)

### 8.3 Calculators (`calculators.py`)

Pure statistical functions — no presentation logic.

**`rank_regions(data, metric, higher_is_better) → DataFrame`**
Adds `rank`, `national_mean`, `vs_national_pct` columns.

**`describe_distribution(values) → DistributionSummary`**
Returns: `mean, median, std, cv, iqr, p10, p90, outliers` (outlier threshold: ±3×IQR).

**`calculate_correlation(x, y) → CorrelationResult`**
Pearson r + p-value + strength label:
```
|r| ≥ 0.9 → very strong
|r| ≥ 0.7 → strong
|r| ≥ 0.5 → moderate
|r| ≥ 0.3 → weak
|r| < 0.3 → negligible
```
Returns: `r, p_value, n, significant (p<0.05), strength, direction`.

**`calculate_gap_to_target(values, target, weights) → GapAnalysis`**
Returns: `target, n_below_target, pct_below_target, mean_gap, total_gap`.

### 8.4 Chart Data Builder (`chart_data_builder.py`)

Pure functions producing typed JSON payloads consumed by the frontend `ChartRenderer`.

| Function                                                            | Output type          | Notes                                                         |
| ------------------------------------------------------------------- | -------------------- | ------------------------------------------------------------- |
| `build_horizontal_bar(data, title, x_label, y_label, national_avg)` | `horizontal_bar`     | Sorted descending by value                                    |
| `build_scatter_regression(df, x_col, y_col, id_col, ...)`           | `scatter_regression` | Sampled to 2,000 pts; r + p-value on full data                |
| `build_lorenz_curve(values, weights, title, ...)`                   | `lorenz_curve`       | Gini computed; includes reference line (UK income Gini 0.36)  |
| `build_stacked_bar(categories, series, title)`                      | `stacked_bar`        |                                                               |
| `build_grouped_bar(categories, series, title)`                      | `grouped_bar`        |                                                               |
| `build_box_violin(groups, title, unit)`                             | `box_violin`         | IQR fences at ±1.5×IQR; outlier list capped at 50             |
| `build_choropleth(data, title, geography, metric, colour_scale)`    | `choropleth`         | LAD-level aggregation (not LSOA)                              |
| `build_heatmap(x_labels, y_labels, values, title, colour_scale)`    | `heatmap`            |                                                               |
| `build_shap_bar(features, title, model_r2)`                         | `shap_bar`           | Sorted descending by importance                               |
| `build_scatter_clusters(data, cluster_labels, title, ...)`          | `scatter_clusters`   | Sampled to 2,000 pts; Viridis-derived colorblind-safe palette |

### 8.5 Context & Rules (`context.py`, `rules.py`)

**`resolve_context(region, urban_rural) → AnalysisScope`**
- `ALL_REGIONS + all area types` → `AnalysisScope.ALL_REGIONS`
- `SINGLE_REGION + all area types` → `AnalysisScope.SINGLE_REGION`
- Other → `AnalysisScope.SUBSET`

**`RankingRule.should_fire(ctx, n_groups) → bool`**
Returns True only when n_groups ≥ 2 and scope permits ranking.

### 8.6 Jinja2 Templates (`intelligence/templates/`)

30 templates covering all chart types:

| Template                   | Used by sections                      |
| -------------------------- | ------------------------------------- |
| `ranking.j2`               | a1, a2, b1, b4, f6, j4, bsa1, ps1–ps4 |
| `coverage_gap.j2`          | a3                                    |
| `equity.j2`                | a4, f1                                |
| `desert_spotlight.j2`      | a5                                    |
| `urban_rural_gap.j2`       | a6, c4, f5                            |
| `gap_to_target.j2`         | a7                                    |
| `ml_prediction.j2`         | a8, d8, g3, g4                        |
| `service_hours.j2`         | b2                                    |
| `weekend_penalty.j2`       | b3                                    |
| `correlation.j2`           | b5, c5, d1–d5                         |
| `distribution.j2`          | c1, c2                                |
| `market_concentration.j2`  | c3, bsa2                              |
| `ml_clusters.j2`           | c6, d6, g1                            |
| `network_topology.j2`      | c7                                    |
| `heatmap.j2`               | d7                                    |
| `equity_decile.j2`         | f2                                    |
| `demographic_breakdown.j2` | f3                                    |
| `accessibility_gap.j2`     | f4                                    |
| `anomaly_spotlight.j2`     | g2                                    |
| `policy_scenario.j2`       | g5, ps1–ps4                           |
| `economic_value.j2`        | j1                                    |
| `bcr_analysis.j2`          | j2                                    |
| `carbon_reduction.j2`      | j3                                    |
| `tier_distribution.j2`     | bsa3                                  |
| `scenario_comparison.j2`   | ps5                                   |
| `single_region.j2`         | (legacy — kept for backward compat)   |
| `coverage_density.j2`      | (legacy — kept for backward compat)   |

> **Note:** Total template files = 30 (25 active + 2 legacy + 3 additional: `distribution.j2`, `heatmap.j2`, `equity_decile.j2`). The engine resolves template by `section_id` key — unknown section_ids are suppressed.

---

## 9. WAREHOUSE PACKAGE (`src/aequitas/warehouse/`)

**Python Files:** 4

### 9.1 Database Schema (`schema.py`)

**Core tables (DDL-defined, populated from Parquet INSERT):**

| Table               | Primary Key                                   | Purpose                                        |
| ------------------- | --------------------------------------------- | ---------------------------------------------- |
| `stops`             | `stop_id` (VARCHAR)                           | NaPTAN England active bus stops                |
| `routes`            | `route_id` (VARCHAR)                          | BODS deduplicated routes                       |
| `lsoa_demographics` | `lsoa_code` (VARCHAR)                         | Master LSOA table with 9 socioeconomic factors |
| `section_results`   | `(region, urban_rural, section_id)` composite | Pre-computed narratives + chart data + stats   |
| `provenance`        | `metric_id` (VARCHAR)                         | Metric → formula → inputs → source files       |

**`section_results` columns:**
```
region      VARCHAR    — ONS region code or "all"
urban_rural VARCHAR    — "all" | "urban" | "rural"
section_id  VARCHAR    — e.g. "f1_gini", "b1_frequency"
stats       JSON       — pre-computed statistics dict
chart_data  JSON       — typed chart payload dict
narrative   VARCHAR    — rendered Jinja2 narrative
```

**Analytics tables (created directly from Parquet via `read_parquet`):**

| Table                   | Parquet source                                     |
| ----------------------- | -------------------------------------------------- |
| `lsoa_service_quality`  | `data/processed/lsoa_service_quality.parquet`      |
| `lsoa_equity_metrics`   | `data/processed/lsoa_equity_metrics.parquet`       |
| `lsoa_accessibility`    | `data/processed/lsoa_2sfca.parquet`                |
| `lsoa_economic`         | `data/processed/lsoa_economic_appraisal.parquet`   |
| `lsoa_policy`           | `data/processed/lsoa_policy_synthesis.parquet`     |
| `route_details`         | `data/processed/route_geometries.parquet`          |
| `lta_readiness`         | `data/processed/lta_franchising_readiness.parquet` |
| `stop_headways`         | `data/audit/stop_headways.parquet`                 |
| `coverage_prediction`   | `data/audit/coverage_prediction.parquet`           |
| `shap_importance`       | `data/audit/shap_importance.parquet`               |
| `route_clusters`        | `data/audit/route_clusters.parquet`                |
| `lsoa_clusters`         | `data/audit/lsoa_clusters_hdbscan.parquet`         |
| `anomalies`             | `data/audit/anomalies.parquet`                     |
| `modal_shift_scenarios` | `data/audit/modal_shift_scenarios.parquet`         |
| `policy_scenarios`      | `data/audit/policy_scenarios.parquet`              |

### 9.2 Warehouse Builder (`builder.py`)

**`build_warehouse(cfg, overwrite=False, section_results=None)`**

Steps:
1. Create/open DuckDB file at `cfg.warehouse_path`
2. Create all core table schemas
3. Load LSOA reference tables from Phase 0 Parquets (`processed/` → `audit/` fallback)
4. Insert pre-computed `section_results` rows (DELETE existing first)
5. Load analytics tables from Parquet via `CREATE TABLE AS SELECT * FROM read_parquet(...)`
6. `CHECKPOINT` to flush WAL

**`get_connection(cfg) → DuckDBPyConnection`**
Opens a read-only connection. Per-request connections are opened and closed by the API layer.

### 9.3 Pre-computation (`precompute.py`)

**`precompute_all_sections(cfg) → list[dict]`**

Iterates all filter combinations and runs InsightEngine for each section. Currently wired for 5 sections:
```python
_SECTIONS = ["coverage_density", "equity", "correlation", "gap_to_target", "policy_scenario"]
```
> **Known gap:** Section registry defines 51 sections; precompute currently covers 5. Expanding this list is the highest-impact next task before Phase 3 deployment.

Filter combinations computed: 30 (10 regions × 3 area types), skipping `region != "all" AND urban_rural != "all"` to reduce redundant subsets.

### 9.4 Provenance (`provenance.py`)

Tracks metric → formula → inputs → source files audit trail. Written to `provenance` table in warehouse.

---

## 10. VALIDATION PACKAGE (`src/aequitas/validation/`)

**Python Files:** 3

### 10.1 Ground Truth Validation (`ground_truth.py`)

**`validate_against_ground_truth(cfg) → dict`**

Loads `data/audit/ground_truth.json` and compares against Phase 0 audit Parquets.

Tolerance modes:
| Mode           | Applied to                                          |
| -------------- | --------------------------------------------------- |
| `exact`        | Triple-deprived LSOA count, scenario count          |
| `within_50`    | Evening isolated, Sunday deserts, Q1 priority LSOAs |
| `within_pct_5` | Gini, Palma, CI, mean SQI                           |

Check families:

| Check name               | Source Parquet                  | Expected |
| ------------------------ | ------------------------------- | -------- |
| `gini_coefficient`       | `lsoa_equity_metrics.parquet`   | 0.5741   |
| `palma_ratio`            | `lsoa_equity_metrics.parquet`   | 5.702    |
| `concentration_index`    | `lsoa_equity_metrics.parquet`   | +0.1358  |
| `mean_sqi`               | `lsoa_service_quality.parquet`  | 65.4     |
| `evening_isolated_lsoas` | `lsoa_service_quality.parquet`  | 5,189    |
| `sunday_desert_lsoas`    | `lsoa_service_quality.parquet`  | 6,745    |
| `q1_priority_lsoas`      | `lsoa_policy_synthesis.parquet` | varies   |
| `triple_deprived_lsoas`  | `lsoa_policy_synthesis.parquet` | 612      |
| `policy_scenarios_count` | `policy_scenarios.parquet`      | varies   |

Returns: `{checks, n_pass, n_warn, n_fail, all_pass}`.

### 10.2 Validation Gates (`gates.py`)

Pre-stage gates applied before each pipeline stage proceeds. Match rate < 95% on spatial joins raises warning and halts unless overridden.

### 10.3 Report Generator (`report.py`)

Writes Markdown validation report to `data/processed/validation_report.md`.

---

## 11. RAG INDEX BUILDER (`src/aequitas/rag/`)

**Python Files:** 1

**`build_faiss_index(cfg) → dict`**

1. Load all non-suppressed narratives from `section_results` in DuckDB
2. Chunk each narrative by paragraph (500 char proxy for token limit — safe for all-MiniLM-L6-v2 max 256 tokens)
3. Embed with `all-MiniLM-L6-v2` (384-dim, CPU, normalized embeddings)
4. Build `faiss.IndexFlatIP` (inner product on L2-normalized vectors = cosine similarity)
5. Save: `data/faiss_index.bin` + `data/faiss_metadata.json`

**Metadata per chunk:**
```json
{
  "section_id": "f1_gini",
  "region": "all",
  "urban_rural": "all",
  "text": "chunk text..."
}
```

Returns: `{n_narratives, n_chunks, index_path, metadata_path}`.

**`chunk_narrative(text, max_tokens=500) → list[str]`**
Splits on double newlines. If a paragraph exceeds max_tokens, includes as-is (no mid-sentence break).

---

*Continued in Part 2: API Layer — Endpoints, Auth, Routing, RAG Chat*



# Aequitas Platform — Master Reference Document
## Part 2 of 3: API Layer — Endpoints, Auth, Routing & RAG Chat

---

## 12. API OVERVIEW

**Location:** `src/aequitas/api/`
**Framework:** FastAPI 0.115 + uvicorn[standard]
**Python Files:** 16

### 12.1 Application Factory (`app.py`)

`create_app() → FastAPI` — creates the app with CORS, lifespan, and all routers.

**CORS policy:**
```
allow_origins:     cfg.cors_origins  (from AEQUITAS_CORS_ORIGINS env — never "*")
allow_credentials: True
allow_methods:     GET, POST, DELETE
allow_headers:     Authorization, Content-Type
```

**Lifespan** (`deps.py`): loads DuckDB path, FAISS index, and embedding model on startup; clears on shutdown.

**Health endpoint (inline in factory):**

| Method | Path          | Auth | Purpose                                                      |
| ------ | ------------- | ---- | ------------------------------------------------------------ |
| GET    | `/api/health` | None | Verifies DuckDB connectivity — returns `{status, warehouse}` |

### 12.2 API Configuration (`config.py`)

`ApiConfig` dataclass — all values from environment variables:

```
db_path             Path   — AEQUITAS_DB_PATH (default: data/aequitas.duckdb)
faiss_index_path    Path   — AEQUITAS_FAISS_INDEX (default: data/faiss_index.bin)
faiss_metadata_path Path   — AEQUITAS_FAISS_METADATA (default: data/faiss_metadata.json)
gemini_api_key      str    — GEMINI_API_KEY
cors_origins        list   — AEQUITAS_CORS_ORIGINS (comma-separated)
supabase_jwt_secret str    — SUPABASE_JWT_SECRET
```

---

## 13. AUTHENTICATION (`api/auth.py`)

**Mechanism:** Supabase JWT (HS256, `audience="authenticated"`)

**`verify_supabase_jwt(credentials) → dict`**

Used as a FastAPI dependency: `Depends(verify_supabase_jwt)`. Returns decoded JWT payload containing `sub` (user ID).

**Validation flow:**
1. Check `DEV_AUTH_BYPASS` — allowed only if `ENVIRONMENT != production` AND `DEV_AUTH_BYPASS=true`
2. If `supabase_jwt_secret` is empty → raise HTTP 500 (never 200/fake)
3. If no `Authorization` header → raise HTTP 401
4. `jose.jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")`
5. On `JWTError` → raise HTTP 401

**Dev bypass (local only):**
```
ENVIRONMENT=development
DEV_AUTH_BYPASS=true
```
Returns `{"sub": "dev-user"}` and logs a warning. Never bypasses in production.

**Which endpoints require auth:**

| Endpoint                                | Auth required                        |
| --------------------------------------- | ------------------------------------ |
| `POST /api/chat`                        | YES — `Depends(verify_supabase_jwt)` |
| `GET /api/conversations`                | YES                                  |
| `POST /api/conversations`               | YES                                  |
| `GET /api/conversations/{id}/messages`  | YES                                  |
| `POST /api/conversations/{id}/messages` | YES                                  |
| `DELETE /api/conversations/{id}`        | YES                                  |
| `GET /api/sections`                     | NO — public                          |
| `GET /api/overview`                     | NO — public                          |
| `GET /api/lsoa/{table}`                 | NO — public                          |
| `GET /api/provenance/{metric_id}`       | NO — public                          |
| `GET /api/metrics/ticker`               | NO — public                          |
| `GET /api/export/{dimension}`           | NO — public                          |
| `GET /api/health`                       | NO — public                          |

> **Note:** Section, overview, LSOA, and export endpoints serve pre-computed read-only analytics — no PII, so no auth is required by design.

---

## 14. DEPENDENCY INJECTION (`api/deps.py`)

Global `_state` dict holds shared resources loaded once at startup.

**`get_db() → Generator[DuckDBPyConnection | None]`**
FastAPI dependency — opens a **fresh read-only DuckDB connection per request**, closes in `finally`. Returns `None` if warehouse was not found at startup. No connection pool — DuckDB read-only connections are cheap.

**`get_faiss() → (faiss_index | None, faiss_metadata | None)`**
Returns FAISS index + metadata list from `_state`. Both `None` if FAISS was not loaded at startup.

**`get_embedding_model() → SentenceTransformer | None`**
Returns `all-MiniLM-L6-v2` model or `None`.

**Startup sequence (`lifespan`):**
1. Check `cfg.db_path.exists()` → store path in `_state["db_path"]`
2. Check `cfg.gemini_api_key` → log warning if missing
3. Check `cfg.faiss_index_path.exists()`:
   - Load `faiss.read_index(path)` → `_state["faiss_index"]`
   - Load `faiss_metadata.json` → `_state["faiss_metadata"]`
   - Load `SentenceTransformer("all-MiniLM-L6-v2")` → `_state["embedding_model"]`
4. On shutdown: `_state.clear()`

API still starts (degraded mode) if DuckDB or FAISS is missing — endpoints return empty results rather than crashing.

---

## 15. ENDPOINT REFERENCE

### 15.1 Overview Router (`api/routers/overview.py`)

| Method | Path            | Auth | Purpose                             |
| ------ | --------------- | ---- | ----------------------------------- |
| GET    | `/api/overview` | None | Headline stats for all 8 dimensions |

**Query params:**
```
region      string  — ONS region code or "all" (default: "all")
urban_rural string  — "all" | "urban" | "rural" (default: "all")
```

**Response schema (`OverviewResponse`):**
```json
{
  "dimensions": [
    {
      "id": "equity",
      "name": "Equity & Deprivation",
      "headline_stat": {
        "value": 0.5741,
        "label": "Disparity ratio",
        "severity": "high"
      },
      "summary": "",
      "route": "/equity"
    }
  ]
}
```

**Severity thresholds per dimension:**

| Dimension       | High                    | Medium | Direction                  |
| --------------- | ----------------------- | ------ | -------------------------- |
| equity          | ≥ 3.0 (disparity ratio) | ≥ 2.0  | Higher = worse             |
| accessibility   | ≥ 90.0 (% covered)      | ≥ 70.0 | Higher = better            |
| service_quality | ≥ 0.3 (trips/capita)    | ≥ 0.15 | Higher = better            |
| route_network   | ≥ 2500 (HHI)            | ≥ 1500 | Higher = more concentrated |
| correlations    | ≥ 0.3 (\|r\|)           | ≥ 0.1  | Higher absolute = stronger |

**Headline section per dimension (from `section_results` table):**

| Dimension        | section_id                 | stat_key                     |
| ---------------- | -------------------------- | ---------------------------- |
| equity           | f1_gini                    | gini                         |
| accessibility    | a3_walking_distance        | pct_covered                  |
| service_quality  | b1_frequency               | national_avg                 |
| route_network    | c3_operator_hhi            | hhi                          |
| correlations     | d1_coverage_deprivation    | r                            |
| economic         | j3_carbon                  | co2_saving_tonnes            |
| bus_services_act | bsa1_franchising_readiness | national_avg                 |
| scenarios        | ps1_freq_restoration       | scenario.population_affected |

---

### 15.2 Sections Router (`api/routers/sections.py`)

| Method | Path            | Auth | Purpose                               |
| ------ | --------------- | ---- | ------------------------------------- |
| GET    | `/api/sections` | None | All sections for a dimension + filter |

**Query params:**
```
dimension   string  — REQUIRED — one of 8 dimension IDs
region      string  — ONS region code or "all" (default: "all")
urban_rural string  — "all" | "urban" | "rural" (default: "all")
```

**Response schema (`SectionsResponse`):**
```json
{
  "dimension": "equity",
  "sections": [
    {
      "section_id": "f1_gini",
      "dimension": "equity",
      "stats": { "gini": 0.5741, "palma": 5.702 },
      "chart_data": { "type": "lorenz_curve", "gini": 0.5741, ... },
      "narrative": "England's bus service distribution...",
      "suppressed": false
    }
  ]
}
```

**Dimension → section_id prefix mapping (controls which sections are returned):**

| Dimension        | Prefix pattern           |
| ---------------- | ------------------------ |
| equity           | `f[0-9]...`              |
| accessibility    | `a[0-9]...`              |
| service_quality  | `b[0-9]...`              |
| route_network    | `c[0-9]...`              |
| correlations     | `d[0-9]...`, `g[0-9]...` |
| economic         | `j[0-9]...`              |
| bus_services_act | `bsa%`                   |
| scenarios        | `ps%`                    |

> **Note:** Single-char prefixes use regex `^{p}[0-9]` to avoid `b%` matching `bsa*`.

---

### 15.3 LSOA Router (`api/routers/lsoa.py`)

| Method | Path                | Auth | Purpose                   |
| ------ | ------------------- | ---- | ------------------------- |
| GET    | `/api/lsoa/{table}` | None | LSOA-level analytics data |

**Path param `table` — allowed values only:**
```
lsoa_service_quality
lsoa_equity_metrics
lsoa_accessibility
lsoa_economic
lsoa_policy
route_details
lta_readiness
```
Any other value → HTTP 400.

**Query params:**
```
region  string  — ONS region code to filter (optional)
fields  string  — comma-separated field names (optional; validated: ^[a-zA-Z_][a-zA-Z0-9_]*$)
limit   int     — 1–50,000 (optional)
```

**Response schema (`LsoaResponse`):**
```json
{ "rows": [...], "total": 33755 }
```

---

### 15.4 Provenance Router (`api/routers/provenance.py`)

| Method | Path                          | Auth | Purpose                  |
| ------ | ----------------------------- | ---- | ------------------------ |
| GET    | `/api/provenance/{metric_id}` | None | Audit trail for a metric |

**Response (`ProvenanceResponse`):**
```json
{
  "metric_id": "gini_coefficient",
  "value": 0.5741,
  "formula": "1 - 2 * trapezoid(lorenz_y, lorenz_x)",
  "inputs": { "source": "lsoa_equity_metrics.parquet" },
  "source_files": ["data/audit/lsoa_equity_metrics.parquet"]
}
```
Returns HTTP 404 if metric not found.

---

### 15.5 Metrics Ticker Router (`api/routers/metrics.py`)

| Method | Path                  | Auth | Purpose                                 |
| ------ | --------------------- | ---- | --------------------------------------- |
| GET    | `/api/metrics/ticker` | None | Headline KPI stats for scrolling ticker |

**Response — list of ticker items:**
```json
[
  { "key": "gini", "label": "Gini Coefficient", "value": "0.5741", "sub": "bus service inequality" },
  { "key": "palma", "label": "Palma Ratio", "value": "5.702×", "sub": "top 10% vs bottom 40%" },
  { "key": "concentration_index", "label": "Concentration Index", "value": "+0.1358", "sub": "pro-rich bias" },
  { "key": "evening_isolated", "label": "Evening Isolated", "value": "15.4%", "sub": "5,189 LSOAs" },
  { "key": "sunday_deserts", "label": "Sunday Deserts", "value": "20.0%", "sub": "6,745 LSOAs" },
  { "key": "mean_sqi", "label": "Mean SQI", "value": "65.4", "sub": "out of 100" }
]
```

> **Known gap:** The live warehouse query targets section IDs `equity_gini`, `equity_palma`, etc. — but actual section IDs are `f1_gini`, `b1_frequency`, etc. The warehouse query always misses and returns the hardcoded Phase 0 fallback. Fix: update query to match actual section_id naming scheme.

---

### 15.6 Chat Router (`api/routers/chat.py`)

| Method | Path        | Auth      | Purpose                        |
| ------ | ----------- | --------- | ------------------------------ |
| POST   | `/api/chat` | YES — JWT | SSE-streamed RAG chat response |

**Request schema (`ChatRequest`):**
```json
{
  "query": "Which regions have the worst evening bus coverage?",
  "context": { "dimension": "service_quality", "region": "all", "urban_rural": "all" },
  "conversation_id": "uuid-or-null",
  "history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

**Rate limiting:** 10 requests per 60 seconds per user (`sub` from JWT). In-memory dict — not shared across multiple worker processes.

**Flow:**
1. Check rate limit
2. Verify FAISS + embedding model loaded (HTTP 503 if not)
3. `retrieve_chunks(query, embedding_model, faiss_index, faiss_metadata, top_k=5)`
4. `build_prompt(query, chunks, context, history[-6:])`
5. Return `EventSourceResponse(stream_gemini(messages, api_key, conversation_id, source_sections))`

**SSE event types:**

| Event   | Data shape                                                 | Notes                   |
| ------- | ---------------------------------------------------------- | ----------------------- |
| `chunk` | `{"text": "..."}`                                          | Streaming text fragment |
| `done`  | `{"conversation_id": "uuid", "sources": ["f1_gini", ...]}` | End of stream           |
| `error` | `{"message": "...", "code": "gemini_error"}`               | On Gemini failure       |

---

### 15.7 Conversations Router (`api/routers/conversations.py`)

Full CRUD for persisted chat sessions via Supabase admin client.

| Method | Path                               | Auth | Purpose                                            |
| ------ | ---------------------------------- | ---- | -------------------------------------------------- |
| GET    | `/api/conversations`               | YES  | List user's conversations (newest first, limit 50) |
| POST   | `/api/conversations`               | YES  | Create conversation `{"title": "..."}` → 201       |
| GET    | `/api/conversations/{id}/messages` | YES  | Messages with pagination (offset, limit 1–500)     |
| POST   | `/api/conversations/{id}/messages` | YES  | Add message → 201; verifies ownership              |
| DELETE | `/api/conversations/{id}`          | YES  | Delete conversation (messages cascade) → 204       |

**Message roles:** `"user"` or `"assistant"` — HTTP 400 on any other value.

**Ownership enforcement on message POST:** Checks `conversations.user_id == jwt.sub` before inserting message. Returns HTTP 404 if not found.

**`updated_at` touch:** Conversation `updated_at` is refreshed on every new message.

---

### 15.8 Export Router (`api/routers/export.py`)

| Method | Path                      | Auth | Purpose                                     |
| ------ | ------------------------- | ---- | ------------------------------------------- |
| GET    | `/api/export/{dimension}` | None | Download PDF report for dimension + filters |

**Query params:**
```
region      string  — default "all"
urban_rural string  — default "all"
```

**PDF structure (ReportLab, A4):**
1. Cover: dimension name, region/area type, disclaimer ("NOT OFFICIAL DfT GUIDANCE")
2. Per section: title, stats table (metric → value), narrative (truncated at 2,000 chars)

**Filename sanitization:** `re.sub(r"[^a-zA-Z0-9_-]", "_", f"aequitas_{dimension}_{region}_{urban_rural}")`

**Response:** `StreamingResponse` with `Content-Disposition: attachment; filename="...pdf"` and `Content-Type: application/pdf`.

> **Security note:** No authentication required — analytics data is read-only with no PII. Any user knowing the URL pattern can download reports. Intentional for shareable policy exports.

---

## 16. WAREHOUSE SERVICE (`api/services/warehouse.py`)

Internal query helpers — never called directly from outside the API layer.

### `query_sections(db, dimension, region, urban_rural) → list[dict]`

Builds a SQL `WHERE` clause from the dimension → prefix mapping. Returns all matching `(section_id, stats, chart_data, narrative)` rows, ordered by `section_id`.

**SQL injection protection:**
- Prefixes come exclusively from the `DIMENSION_PREFIXES` constant dict — never user input
- Single-char prefixes (e.g. `"b"`) use `regexp_matches(section_id, '^b[0-9]')` to prevent `b%` matching `bsa*`
- Multi-char prefixes (e.g. `"bsa"`) use `LIKE 'bsa%'`
- `region` and `urban_rural` always passed as `?` parameterised values

### `query_overview(db, region, urban_rural) → list[dict]`

Iterates `HEADLINE_SECTIONS` dict, queries `section_results` per dimension. Supports dot-path stat keys like `"scenario.population_affected"`. Extracts scalar from nested dict using `national_avg` → `value` fallback chain.

### `query_lsoa(db, table, region, fields, limit) → (list[dict], int)`

**SQL injection protection:**
- `table` validated against `ALLOWED_TABLES` allowlist (7 tables)
- Field names validated: `^[a-zA-Z_][a-zA-Z0-9_]*$` regex — raises `ValueError` on any other pattern
- `region` passed as `?` parameterised value
- `limit` cast to `int()` before interpolation

### `query_provenance(db, metric_id) → dict | None`

Simple parameterised query on `provenance` table.

---

## 17. RAG SERVICE (`api/services/rag.py`)

### `retrieve_chunks(query, embedding_model, faiss_index, faiss_metadata, top_k=5, context=None) → list[dict]`

1. `embedding_model.encode([query], normalize_embeddings=True)` → 384-dim float32 vector
2. `faiss_index.search(query_np, top_k)` → scores + indices
3. Returns copies of metadata chunks with `score` field added

### `build_prompt(query, chunks, context=None, history=None) → list[dict]`

Constructs Gemini message list:
1. System message: policy analyst role + evidence-only instruction
2. Ack message from model: `"Understood. I'll answer based on the provided evidence."`
3. History: last 6 messages from `history` (supports both Pydantic `HistoryMessage` objects and raw dicts)
4. Final user query

**System prompt:**
```
You are a UK bus transport policy analyst for the Aequitas platform.
Answer based ONLY on the provided evidence. If the evidence doesn't
cover the question, say so. Be concise and cite specific statistics.
```

Context line added: `"User is viewing {dimension} for region={region} ({urban_rural})."`

### `stream_gemini(messages, api_key, conversation_id=None, source_sections=None) → AsyncGenerator[dict]`

Uses `google.genai` v1.68 (not deprecated `google.generativeai`). Model: `gemini-2.5-flash`.

Converts message list to `genai_types.Content` format, calls `client.models.generate_content_stream()`, yields `chunk` events per text fragment, then `done` event.

On any exception: yields `error` event with sanitised message — never exposes raw API error to client.

> **Known issue:** `generate_content_stream()` is synchronous — the `for chunk in response` loop blocks the event loop inside `async def`. For single-user deployment this is acceptable. For concurrent users, wrap in `asyncio.get_event_loop().run_in_executor()` or switch to the async stream variant.

---

## 18. PYDANTIC REQUEST/RESPONSE MODELS (`api/models/`)

### Requests (`requests.py`)

**`ChatRequest`:**
```
query           str               — user's question
context         dict | None       — {"dimension": str, "region": str, "urban_rural": str}
conversation_id str | None        — UUID or None
history         list[dict] | None — [{role, content}, ...] last N turns
```

### Responses (`responses.py`)

**`SectionItem`:**
```
section_id  str
dimension   str
stats       dict
chart_data  dict
narrative   str
suppressed  bool
```

**`SectionsResponse`:**
```
dimension  str
sections   list[SectionItem]
```

**`HeadlineStat`:**
```
value     float
label     str
severity  str  — "low" | "medium" | "high"
```

**`DimensionOverview`:**
```
id             str
name           str
headline_stat  HeadlineStat
summary        str
route          str  — e.g. "/equity"
```

**`OverviewResponse`:**
```
dimensions  list[DimensionOverview]
```

**`ProvenanceResponse`:**
```
metric_id    str
value        float
formula      str
inputs       dict
source_files list[str]
```

**`LsoaResponse`:**
```
rows   list[dict]
total  int
```

---

## 19. SUPABASE SCHEMA (`supabase/migrations/001_initial.sql`)

All tables have Row Level Security (RLS) enabled. All policies use `auth.uid() = user_id`.

### Tables

**`profiles`** — auto-created on signup via trigger:
```
id           UUID PK → auth.users(id) ON DELETE CASCADE
display_name TEXT
bio          TEXT
policy_interests TEXT[] DEFAULT '{}'
created_at   TIMESTAMPTZ
updated_at   TIMESTAMPTZ
```
RLS: SELECT and UPDATE by owner only. Trigger: `handle_new_user()` inserts profile on `auth.users` INSERT.

**`conversations`** — chat session containers:
```
id       UUID PK DEFAULT gen_random_uuid()
user_id  UUID → auth.users(id) ON DELETE CASCADE NOT NULL
title    TEXT
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```
RLS: ALL operations by owner only.

**`messages`** — individual chat turns:
```
id              UUID PK
conversation_id UUID → conversations(id) ON DELETE CASCADE NOT NULL
user_id         UUID → auth.users(id) ON DELETE CASCADE NOT NULL
role            TEXT NOT NULL CHECK (role IN ('user', 'assistant'))
content         TEXT NOT NULL
created_at      TIMESTAMPTZ
```
RLS: ALL operations by owner only. Cascade delete from conversations.

**`saved_analyses`** — bookmarked narratives / chat responses:
```
id         UUID PK
user_id    UUID → auth.users(id) ON DELETE CASCADE NOT NULL
title      TEXT NOT NULL
content    TEXT NOT NULL
section_id TEXT
dimension  TEXT
tags       TEXT[] DEFAULT '{}'
created_at TIMESTAMPTZ
```
RLS: ALL operations by owner only.

**`policy_notes`** — journal entries per dimension:
```
id         UUID PK
user_id    UUID → auth.users(id) ON DELETE CASCADE NOT NULL
dimension  TEXT NOT NULL
region     TEXT DEFAULT 'all'
stance     TEXT CHECK (stance IN ('priority', 'monitor', 'adequate'))
thesis     TEXT NOT NULL
critique   TEXT
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```
RLS: ALL operations by owner only.

**`saved_regions`** — user's watchlist:
```
id          UUID PK
user_id     UUID → auth.users(id) ON DELETE CASCADE NOT NULL
region_code TEXT NOT NULL
region_name TEXT NOT NULL
notes       TEXT
created_at  TIMESTAMPTZ
```
RLS: ALL operations by owner only.

---

*Continued in Part 3: Frontend Web App, Charts, Hooks & Testing*



# Aequitas Platform — Master Reference Document
## Part 3 of 3: Frontend Web App, Charts, Hooks, Testing & Known Issues

---

## 20. FRONTEND WEB APP

**Location:** `frontend/`
**Framework:** React 19 + Vite 6 + TypeScript 5.9
**State management:** TanStack Query v5 (server state) + URL search params (filter state)
**UI library:** shadcn/ui + Tailwind CSS v4
**Charts:** Observable Plot 0.6 + MapLibre GL 5
**Auth:** Supabase JS v2
**Port:** 5173 (Vite dev server)

---


### 20.1 Project Structure

```
frontend/src/
├── App.tsx                   — root router + providers
├── main.tsx                  — entry point
├── index.css                 — Tailwind v4 theme tokens + animations
├── api/
│   ├── client.ts             — typed fetchJson<T>() base client
│   ├── hooks.ts              — TanStack Query hooks (useOverview, useSections, etc.)
│   └── types.ts              — API response TypeScript types
├── components/
│   ├── auth/                 — ProtectedRoute
│   ├── charts/               — 8 chart components + ChartRenderer dispatcher
│   ├── chat/                 — ChatDrawer, ChatFAB, ChatMessage, ChatSidebar, QuickActions, SuggestedQuestions
│   ├── dimension/            — DimensionPage, SectionCard, ScenarioBuilder, ProvenancePanel
│   ├── home/                 — HomePage, DimensionCard
│   ├── layout/               — AppShell, Header, Footer, TabBar, StatusBar, MetricsTicker, FilterDropdowns, UserMenu
│   ├── saved/                — SavedAnalyses, PolicyNotes, SavedRegions
│   ├── shared/               — EmptyState, Markdown, Severity
│   └── ui/                   — button, collapsible, select, sheet, tooltip (shadcn/ui)
├── contexts/
│   └── AuthContext.tsx        — Supabase auth state provider
├── hooks/
│   └── useChat.ts             — SSE streaming chat hook
├── integrations/
│   └── supabase/client.ts     — Supabase browser client (singleton)
├── lib/
│   ├── colours.ts             — CATEGORICAL palette (colorblind-safe)
│   ├── constants.ts           — DIMENSIONS, REGIONS, AREA_TYPES arrays
│   ├── db.ts                  — Supabase saved analyses / notes / regions helpers
│   └── utils.ts               — cn() classname helper
└── pages/
    ├── AuthPage.tsx
    ├── LandingPage.tsx
    ├── AboutPage.tsx
    ├── DisclaimerPage.tsx
    ├── ContactPage.tsx
    ├── ComparePage.tsx
    └── ProfilePage.tsx
```

---

### 20.2 Routing (`App.tsx`)

All non-dashboard routes are lazy-loaded (`React.lazy`). Loading fallback: indigo pulsing dot.

| Path                        | Component                                   | Auth | Notes                       |
| --------------------------- | ------------------------------------------- | ---- | --------------------------- |
| `/`                         | `LandingPage`                               | None | Public landing              |
| `/about`                    | `AboutPage`                                 | None |                             |
| `/disclaimer`               | `DisclaimerPage`                            | None |                             |
| `/contact`                  | `ContactPage`                               | None |                             |
| `/auth`                     | `AuthPage`                                  | None | Login / signup via Supabase |
| `/dashboard`                | `ProtectedRoute → AppShell → HomePage`      | YES  |                             |
| `/dashboard/:dimensionSlug` | `ProtectedRoute → AppShell → DimensionPage` | YES  | e.g. `/dashboard/equity`    |
| `/compare`                  | `ProtectedRoute → ComparePage`              | YES  | Standalone, no AppShell     |
| `/profile`                  | `ProtectedRoute → ProfilePage`              | YES  |                             |
| `/saved`                    | `ProtectedRoute → SavedAnalyses`            | YES  |                             |
| `/notes`                    | `ProtectedRoute → PolicyNotes`              | YES  |                             |
| `/regions`                  | `ProtectedRoute → SavedRegions`             | YES  |                             |

**QueryClient:** `staleTime: Infinity` on all queries — pre-computed data never re-fetches automatically.

---

### 20.3 Design System

**Dark theme — Bloomberg-dark palette with indigo primary:**

```css
--color-background:        hsl(228, 15%, 4%)    /* near-black */
--color-foreground:        hsl(0, 0%, 95%)      /* near-white */
--color-card:              hsl(228, 15%, 7%)
--color-muted:             hsl(228, 15%, 10%)
--color-muted-foreground:  hsl(228, 10%, 55%)
--color-border:            hsl(228, 15%, 15%)
--color-primary:           hsl(239, 84%, 67%)   /* indigo */
--color-primary-foreground: hsl(0, 0%, 100%)
--radius:                  0.375rem
```

**Animations:**
```
.animate-fade-in     — fade-in 0.3s ease-out (opacity + translateY 6px)
.animate-slide-in    — slide-in-right 0.3s ease-out (opacity + translateX -20px)
.animate-pulse-glow  — pulse-glow 2s infinite (opacity 0.4 → 1)
.chart-animate-in    — chart-fade-in 0.4s ease-out
```

**Chart colour palette (`lib/colours.ts`):**
```typescript
export const CATEGORICAL = [
  "#4e79a7", "#f28e2b", "#e15759", "#76b7b2",
  "#59a14f", "#edc948", "#b07aa1", "#ff9da7"
]
```
Viridis-derived cluster palette used by scatter cluster charts:
```python
["#440154", "#46327e", "#365c8d", "#277f8e", "#1fa187", "#4ac16d", "#9fda3a", "#fde725"]
```

---

### 20.4 Filter State (URL Search Params)

Global filters are stored in URL search params — bookmarkable and shareable.

**`useFilters()` hook:**
```typescript
const { region, urbanRural, setRegion, setUrbanRural } = useFilters()
// reads:  ?region=E12000007&urban_rural=urban
// writes: updates URL without navigation
```

Default values: `region = "all"`, `urbanRural = "all"`.

**REGIONS constant (`lib/constants.ts`):**
```typescript
[
  { code: "all", name: "All England" },
  { code: "E12000001", name: "North East" },
  { code: "E12000002", name: "North West" },
  { code: "E12000003", name: "Yorkshire and The Humber" },
  { code: "E12000004", name: "East Midlands" },
  { code: "E12000005", name: "West Midlands" },
  { code: "E12000006", name: "East of England" },
  { code: "E12000007", name: "London" },
  { code: "E12000008", name: "South East" },
  { code: "E12000009", name: "South West" },
]
```

**AREA_TYPES constant:**
```typescript
[
  { code: "all", name: "All Areas" },
  { code: "urban", name: "Urban" },
  { code: "rural", name: "Rural" },
]
```

---

### 20.5 API Client Layer (`api/`)

**`fetchJson<T>(path, params?) → Promise<T>`** (`api/client.ts`)

Prefixes `/api`, appends query params, throws on non-OK response. Does **not** attach `Authorization` headers — used only for public (no-auth) endpoints.

> **Note:** Auth-required endpoints (`/api/chat`, `/api/conversations`) are called directly via `fetch()` in `useChat.ts` and Supabase helpers — with `Authorization: Bearer {token}` set manually.

**TanStack Query hooks (`api/hooks.ts`):**

| Hook                                         | Endpoint                   | Query key                                       |
| -------------------------------------------- | -------------------------- | ----------------------------------------------- |
| `useFilters()`                               | URL params only            | —                                               |
| `useOverview(region, urbanRural)`            | GET `/api/overview`        | `["overview", region, urbanRural]`              |
| `useSections(dimension, region, urbanRural)` | GET `/api/sections`        | `["sections", dimension, region, urbanRural]`   |
| `useProvenance(metricId)`                    | GET `/api/provenance/{id}` | `["provenance", metricId]` — disabled when null |
| `useLsoa(table, region)`                     | GET `/api/lsoa/{table}`    | `["lsoa", table, region]`                       |

All hooks use `staleTime: Infinity` — data is pre-computed and never stale.

---

### 20.6 AppShell Layout (`components/layout/AppShell.tsx`)

Layout for all protected dashboard routes:
```
<div min-h-screen bg-background flex flex-col>
  <StatusBar />          — top bar (env indicator / version)
  <Header />             — logo, user menu
  <MetricsTicker />      — scrolling ground truth KPIs
  <TabBar />             — dimension navigation tabs
  <main max-w-7xl>
    <Outlet />           — DimensionPage or HomePage
  </main>
  <Footer />
  <ChatFAB />            — floating action button (bottom-right)
  <ChatDrawer />         — slide-over chat panel
</div>
```

`chatOpen` boolean state in AppShell — FAB sets to true, ChatDrawer onClose sets to false.

---

### 20.7 DimensionPage (`components/dimension/DimensionPage.tsx`)

Wrapped in `DimensionErrorBoundary` (class component) — catches render crashes, shows retry button.

**Data flow:**
1. `useParams()` → `dimensionSlug`
2. Look up `DIMENSIONS.find(d => d.route === /${dimensionSlug})`
3. `useSections(dimensionId, region, urbanRural)` → loading skeleton | error state | sections
4. Filter sections: show only where `stats`, `chart_data`, or `narrative` is non-empty
5. `sections.length === 0` → empty state with hint to select "All England"
6. Map sections → `<SectionCard key={section_id} section={s} />`

Scenario dimension shows `<ScenarioBuilder />` above sections.

Export button: `<a href="/api/export/{dimensionId}?{params}" download>` — no JS, direct download link.

---

### 20.8 SectionCard (`components/dimension/SectionCard.tsx`)

Renders one analytical section. Passes `section.chart_data` to `<ChartRenderer chartType={...} chartData={...} />`. Shows narrative as Markdown below chart.

---

## 21. CHART COMPONENTS

All charts follow an identical pattern:
```typescript
const ref = useRef<HTMLDivElement>(null)
useEffect(() => {
  if (!ref.current) return
  const chart = Plot.plot({ ... })
  ref.current.replaceChildren(chart)
  return () => chart.remove()      // cleanup prevents memory leaks
}, [chartData])
return <div ref={ref} aria-label="..." role="img" />
```

**Tooltip style (dark theme, consistent across all charts):**
```
fill:   hsl(228, 15%, 10%)
stroke: hsl(228, 15%, 20%)
color:  hsl(0, 0%, 90%)
```

### 21.1 ChartRenderer (`components/charts/ChartRenderer.tsx`)

Dispatcher — maps `chart_type` string to the correct chart component. Renders `null` for unknown types.

| chart_type           | Component                |
| -------------------- | ------------------------ |
| `horizontal_bar`     | `HorizontalBarChart`     |
| `lorenz_curve`       | `LorenzCurveChart`       |
| `scatter_regression` | `ScatterRegressionChart` |
| `scatter_clusters`   | `ScatterClustersChart`   |
| `box_violin`         | `BoxViolinChart`         |
| `heatmap`            | `HeatmapChart`           |
| `shap_bar`           | `ShapBarChart`           |
| `choropleth`         | `ChoroplethMap`          |

### 21.2 HorizontalBarChart

Observable Plot `barX` mark, sorted descending. Shows national average reference line if `chartData.national_avg` present. Tooltip: `label → value (rank N)`.

**Expected `chartData` shape:**
```json
{
  "type": "horizontal_bar",
  "title": "string",
  "x_label": "string",
  "y_label": "string",
  "data": [{ "label": "London", "value": 0.42, "rank": 1 }],
  "national_avg": 0.28
}
```

### 21.3 LorenzCurveChart

Line chart with diagonal equality line (dashed grey) and shaded area between Lorenz curve and equality line. Subtitle shows Gini coefficient and reference (UK income Gini 0.36).

**Expected `chartData` shape:**
```json
{
  "type": "lorenz_curve",
  "gini": 0.5741,
  "reference_gini": 0.36,
  "reference_label": "UK Income Gini",
  "curve_points": [{ "cum_pop": 0.0, "cum_service": 0.0 }, ...]
}
```

### 21.4 ScatterRegressionChart

`Plot.dot` marks for points + `Plot.line` for regression line. Subtitle shows `r = X.XXX (p = X.XXXXXX, n = XXXXX)`.

**Expected `chartData` shape:**
```json
{
  "type": "scatter_regression",
  "r": -0.0644,
  "p_value": 0.000123,
  "regression_line": { "slope": -0.12, "intercept": 15.4 },
  "sample_size": 33755,
  "data": [{ "x": 42.1, "y": 18.3, "id": "E01000001" }]
}
```

### 21.5 ScatterClustersChart

`Plot.dot` coloured by cluster ID with `Plot.crosshairX` guide line. Legend shows cluster labels and counts.

**Expected `chartData` shape:**
```json
{
  "type": "scatter_clusters",
  "x_label": "PC1",
  "y_label": "PC2",
  "clusters": [{ "id": 0, "label": "Urban High Frequency", "n": 8200 }],
  "data": [{ "x": 1.2, "y": -0.4, "cluster": 0, "id": "E01000001" }]
}
```

### 21.6 BoxViolinChart

`Plot.link` (whisker min→max) + `Plot.rectX` (IQR box) + `Plot.dot` (median) + `Plot.text` (median label). Tooltip shows full 5-number summary.

**Expected `chartData` shape:**
```json
{
  "type": "box_violin",
  "x_label": "Route length (km)",
  "data": [{ "group": "Urban", "min": 1.2, "q1": 5.4, "median": 10.2, "q3": 18.7, "max": 89.3 }]
}
```

> **Known schema mismatch:** Backend `build_box_violin()` produces key `"label"` but `BoxViolinChart` reads key `"group"`. Sections c1 (route length) and c2 (stops per route) will render empty box plots until this is fixed. Fix: change `BoxViolinChart` line 24 to `const data = (chartData.data ?? []) as BoxDatum[]` and update interface to accept `label` or add mapping `group: d.label ?? d.group`.

### 21.7 HeatmapChart

`Plot.cell` with `YlOrRd` colour scheme + text values overlaid (white text when `value > 50`).

**Expected `chartData` shape:**
```json
{
  "type": "heatmap",
  "x_labels": ["IMD 1", "IMD 2", ...],
  "y_labels": ["Urban", "Rural"],
  "values": [[12.3, 8.7, ...], [5.1, 3.2, ...]]
}
```

### 21.8 ShapBarChart

`Plot.barX` sorted descending by importance. Subtitle shows `Model R² = X.XXX`. Value labels right-aligned next to each bar.

**Expected `chartData` shape:**
```json
{
  "type": "shap_bar",
  "title": "Feature importance (SHAP)",
  "model_r2": 0.472,
  "features": [{ "name": "nocar_pct", "importance": 0.1823 }]
}
```

### 21.9 ChoroplethMap (MapLibre GL)

Full GeoJSON rendering using MapLibre GL 5. LAD-level aggregation (not LSOA — too many polygons for browser rendering).

---

## 22. CHAT SYSTEM

### 22.1 `useChat` Hook (`hooks/useChat.ts`)

Manages SSE streaming, message state, and conversation ID.

**State:**
```typescript
messages:    Message[]     — [{id, role: "user"|"assistant", content}]
isStreaming: boolean
error:       string | null
conversationId: ref        — persists across renders without re-triggering effects
```

**`sendMessage(query, context)`:**
1. Abort any in-flight stream via `AbortController`
2. Append user message + empty assistant placeholder
3. GET Supabase session → Bearer token (falls back to `"dev"` if no session)
4. `fetch("/api/chat", { method: "POST", signal, body: JSON.stringify({...}) })`
5. Parse SSE stream manually (maintains `currentEventType` buffer, resets on blank line per SSE spec)
6. On `chunk` event: append text to last assistant message
7. On `done` event: store `conversation_id` in ref
8. On `error` event: set error state, remove empty placeholder
9. On `AbortError`: silently return (user started new message)

**History sent:** Last 6 messages from `messagesRef.current` (not state — avoids stale closure).

**`clearMessages()`:** Aborts in-flight stream, resets messages/conversation_id/error.

### 22.2 ChatDrawer (`components/chat/ChatDrawer.tsx`)

Slide-over panel from the right. Contains `ChatSidebar` (conversation list), `ChatMessage` list, input box, and `SuggestedQuestions`.

### 22.3 ChatFAB (`components/chat/ChatFAB.tsx`)

Floating action button bottom-right, shown on all dashboard pages. Clicking sets `chatOpen = true` in AppShell.

---

## 23. AUTHENTICATION (`contexts/AuthContext.tsx`)

Thin wrapper over Supabase JS v2 auth.

**Context value:**
```typescript
{
  user:         User | null        — Supabase auth user
  session:      Session | null
  loading:      boolean
  signIn:       (email, password) => Promise<void>
  signUp:       (email, password) => Promise<void>
  signOut:      () => Promise<void>
}
```

**`ProtectedRoute`** (`components/auth/ProtectedRoute.tsx`): Redirects to `/auth` if `loading=false && !user`. Shows nothing while loading.

---

## 24. TEST SUITE

**Python tests:** pytest, 244 passing

**Test directory structure:**
```
tests/
├── conftest.py
├── core/          — test_config, test_constants, test_models, test_types, test_validators
├── ingestion/     — test_bods, test_census, test_imd, test_naptan, test_poi
├── processing/    — test_dedup, test_demographics, test_route_geometry, test_service_quality, test_spatial
├── analytics/     — test_accessibility, test_economic, test_equity, test_ml_anomaly,
│                     test_ml_clustering, test_ml_prediction, test_policy_synthesis, test_shap_export
├── intelligence/  — test_calculators, test_chart_data_builder, test_context, test_engine,
│                     test_rules, test_rules_new, test_section_registry, test_templates_new
├── warehouse/     — test_builder, test_chart_types, test_precompute, test_precompute_30, test_schema
├── validation/    — test_gates, test_ground_truth
├── pipeline/      — test_cli
├── rag/           — test_index_builder  ← requires faiss-cpu
├── api/           — test_chat, test_integration, test_lsoa, test_overview,  ← requires fastapi[testclient]
│                     test_provenance, test_sections
├── integration/   — test_full_pipeline  ← marked @pytest.mark.slow
├── test_narrative_length.py
└── test_precompute_30.py
```

**Run core tests (no FAISS/FastAPI):**
```bash
uv run python -m pytest tests/core tests/analytics tests/intelligence \
  tests/processing tests/ingestion tests/pipeline tests/validation tests/warehouse -q
```

**Test environment requirements:**
```
pandas, numpy, geopandas, scikit-learn, hdbscan, shap  — all from pyproject.toml
faiss-cpu                                               — required for tests/rag/
fastapi[testclient]                                     — required for tests/api/
```

**Frontend tests:** Vitest + React Testing Library

```bash
cd frontend && npm run test
```

Test files:
```
frontend/src/components/auth/__tests__/ProtectedRoute.test.tsx
frontend/src/components/charts/__tests__/ChartRenderer.test.tsx
```

---

## 25. CLAUDE AUTOMATION (`.claude/`)

### Hooks

| Hook                   | Trigger       | Purpose                                              |
| ---------------------- | ------------- | ---------------------------------------------------- |
| `guard-destructive.sh` | Pre-bash      | Blocks destructive git commands without confirmation |
| `post-write-lint.sh`   | Post-write    | Runs ruff lint on modified Python files              |
| `session-start.sh`     | Session start | Loads project context, checks phase                  |
| `update-phase.sh`      | Phase change  | Updates MEMORY.md current phase                      |

### Rules Files (`.claude/rules/`)

| File                     | Enforces                                                                     |
| ------------------------ | ---------------------------------------------------------------------------- |
| `data-quality.md`        | 9 socioeconomic factors, entity counting, data traps, validation gates       |
| `figures.md`             | Every number must be in `docs/figures-registry.md` before use                |
| `frontend.md`            | TypeScript strict, ≤200 line components, no business logic in components     |
| `intelligence-engine.md` | No LLM in InsightEngine, TAG constants from `constants.py`, 30 filter combos |
| `python-pipeline.md`     | Type hints, Pydantic v2, loguru, no bare except, ≤50 line functions          |

### Skills (`.claude/skills/`)

| Skill              | Purpose                                         |
| ------------------ | ----------------------------------------------- |
| `aequitas-context` | Load full project context at session start      |
| `data-audit`       | Guide for Phase 0-style data audit tasks        |
| `run-pipeline`     | Guide for running and debugging pipeline stages |

---

## 26. KNOWN ISSUES & GAPS

### Critical

| #   | Issue                                          | Location                                                          | Impact                                                                      |
| --- | ---------------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------- |
| 1   | **Box-violin schema mismatch**                 | `BoxViolinChart.tsx` reads `d.group`; backend produces `d.label`  | Sections c1, c2 render empty charts                                         |
| 2   | **Metrics ticker wrong section IDs**           | `metrics.py` queries `equity_gini`; actual IDs are `f1_gini` etc. | Ticker always shows hardcoded fallback, never live warehouse                |
| 3   | **Precompute covers 5 of 51 sections**         | `warehouse/precompute.py` `_SECTIONS` list                        | Most DimensionPage views show empty (no sections pass the non-empty filter) |
| 4   | **Synchronous Gemini call in async generator** | `api/services/rag.py` `stream_gemini()`                           | Blocks event loop during generation; concurrent chat requests queue         |

### Notable

| #   | Issue                                                  | Location                                         | Impact                                                                                                 |
| --- | ------------------------------------------------------ | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| 5   | `cfg._section_results` dynamic attribute               | `pipeline/_stages.py` Stage 4→5                  | Breaks if stages run in separate processes                                                             |
| 6   | Supabase client created per request                    | `api/routers/conversations.py` `_get_supabase()` | Inefficient for conversation-heavy usage                                                               |
| 7   | `ApiConfig()` instantiated per auth call               | `api/auth.py` `verify_supabase_jwt()`            | Minor env-var re-read overhead per request                                                             |
| 8   | FAISS chunking uses character proxy for tokens         | `rag/index_builder.py`                           | 500 chars ≈ 125 tokens; safe but could be 2× larger for better RAG context                             |
| 9   | `shap_summary.csv` vs `shap_importance.parquet` naming | `warehouse/schema.py`                            | Phase 0 produced `shap_summary.csv`; schema expects `.parquet` — `shap_importance` table will be empty |
| 10  | No CI/CD configuration                                 | Root                                             | Phase 3 not started — no automated test pipeline                                                       |
| 11  | Export endpoint has no auth                            | `api/routers/export.py`                          | Intentional for shareable reports; worth an explicit comment                                           |

---

## 27. PHASE 0 NOTEBOOKS INVENTORY

All 30 notebooks in `notebooks/`. Phase 0 complete as of 2026-03-14 (19 active notebooks, 103 checks, 0 FAIL).

### Series 02 — Data Understanding & Baseline
| Notebook                            | Purpose                         | Key output                                       |
| ----------------------------------- | ------------------------------- | ------------------------------------------------ |
| `02_data_understanding.ipynb`       | Initial data exploration        | —                                                |
| `02a_column_inventory.ipynb`        | Column audit across all sources | `gias_column_inventory.csv`                      |
| `02b_bods_deep_dive.ipynb`          | BODS GTFS deep analysis         | Route/trip counts confirmed                      |
| `02c_spatial_analysis.ipynb`        | Spatial join NaPTAN → LSOA      | Match rate confirmed                             |
| `02d_imd_subdomain_deep_dive.ipynb` | IMD 2025 subdomain analysis     | 9 factors confirmed                              |
| `02e_multivariate_clustering.ipynb` | LSOA clustering (HDBSCAN + GMM) | `lsoa_feature_matrix_clustered.parquet`          |
| `02f_cross_factor_synthesis.ipynb`  | Cross-factor correlation matrix | —                                                |
| `02g_bods_service_levels.ipynb`     | Service levels per LSOA         | `lsoa_service_levels.parquet` (zero-filled trap) |
| `02h_spatial_access.ipynb`          | 2SFCA accessibility             | `lsoa_accessibility.parquet`                     |
| `02i_lsoa_stories.ipynb`            | Case studies per LSOA archetype | `top_500_transport_deserts.csv`                  |

### Series 03 — Additional Data Sources
| Notebook                        | Purpose                          | Key output                                    |
| ------------------------------- | -------------------------------- | --------------------------------------------- |
| `03a_disability_ts038.ipynb`    | Census TS038 disability data     | Merged into master_lsoa_table                 |
| `03b_hospitals.ipynb`           | NHS ODS hospital geocoding       | `hospitals_geocoded.parquet` (3,714 rows)     |
| `03c_gp_surgeries.ipynb`        | NHS ODS GP geocoding             | `gp_surgeries_geocoded.parquet` (12,059 rows) |
| `03d_schools_gias.ipynb`        | GIAS school geocoding            | `schools_geocoded.parquet` (3,336 secondary)  |
| `03e_employment_bres.ipynb`     | NOMIS BRES 2023 MSOA employment  | `lsoa_employment_proxy.parquet`               |
| `03f_tag_databook.ipynb`        | TAG v2.03fc value extraction     | `tag_constants.json`                          |
| `03g_desnz_carbon.ipynb`        | DESNZ 2025 GHG factor extraction | `desnz_carbon_factors.json`                   |
| `03h_codepoint_postcodes.ipynb` | Code-Point Open postcode lookup  | `postcode_lookup.parquet` (1,492,016 rows)    |

### Series 04 — Analytics & Modelling
| Notebook                          | Purpose                                           | Key output                                                                                                                                                                                  |
| --------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `04a_route_geometry.ipynb`        | Haversine route lengths, LA crossing              | `route_geometries.parquet`                                                                                                                                                                  |
| `04b_service_quality_depth.ipynb` | Headway stats, SQI, evening/Sunday flags          | `lsoa_service_quality.parquet`, `stop_headways.parquet`                                                                                                                                     |
| `04c_equity_framework.ipynb`      | Gini, Palma, CI, triple-deprived                  | `lsoa_equity_metrics.parquet`, `equity_summary.json`                                                                                                                                        |
| `04d_ml_suite.ipynb`              | Random Forest + SHAP + anomaly                    | `coverage_prediction.parquet`, `shap_summary.csv`, `anomalies.parquet` — Note: Phase 0 produced `shap_summary.csv`; warehouse schema expects `shap_importance.parquet` (see Known Issue #9) |
| `04e_economic_appraisal.ipynb`    | BCR, modal shift, carbon                          | `lsoa_economic_appraisal.parquet`                                                                                                                                                           |
| `04f_policy_synthesis.ipynb`      | Priority matrix, franchising readiness, scenarios | `lsoa_policy_synthesis.parquet`, `lta_franchising_readiness.parquet`, `policy_scenarios.parquet`                                                                                            |

---

## 28. DATA QUALITY RULES (CRITICAL TRAPS)

These are the non-obvious data traps discovered during Phase 0. Every pipeline contribution must know these.

| Trap                        | Rule                                                                                                 |
| --------------------------- | ---------------------------------------------------------------------------------------------------- |
| NaPTAN Status field         | Use `'active'` not `'act'` — confirmed in audit (act=0 rows)                                         |
| NaPTAN stop types           | Filter to BCT/BCS/BCE only — never include rail, tram, ferry                                         |
| NaPTAN KDTree alignment     | Always `reset_index(drop=True)` after filtering before building KDTree                               |
| BODS counting               | Count routes (route_id), not journey patterns — one route has many patterns                          |
| BODS cross-region           | Same route in 2 regional BODS feeds = 1 route — dedup mandatory                                      |
| BODS shape_dist_traveled    | 100% null — always compute route lengths via Haversine                                               |
| BODS trips without geometry | 48.5% lack shape_id — flag `has_geometry=False`, never drop                                          |
| BODS stop_times.txt         | 5.8 GB — read in 1M-row chunks, never load fully into memory                                         |
| lsoa_service_levels.parquet | `total_weekday_trips` is zero-filled — use `lsoa_service_quality.parquet → total_weekday_departures` |
| IMD version                 | Use IMD 2025 (2021 LSOA boundaries) — IMD 2019 is obsolete                                           |
| Population denominator      | ALWAYS 56,490,056 — never pipeline-filtered population                                               |
| ONS boundaries vintage      | 2022 vintage (RGN22CD/RGN22NM) — detect column names dynamically                                     |
| NumPy 2.x                   | `np.trapz` removed — use `np.trapezoid` with `hasattr` guard                                         |
| GIAS encoding               | `latin-1` not `utf-8`                                                                                |
| NHS ODS API                 | Offset starts at 1 (not 0); use `Next-Page` header for pagination                                    |
| NOMIS BRES                  | LSOA level suppressed — use MSOA (TYPE297), `date=2023`, `employment_status=1`                       |
| stops_per_1000 > 30         | Indicates stop-route double counting — `RegionSummary` validator hard-rejects                        |

---

## 29. ENDPOINT COUNT SUMMARY

| Router          | Endpoints |
| --------------- | --------- |
| overview        | 1         |
| sections        | 1         |
| lsoa            | 1         |
| provenance      | 1         |
| metrics         | 1         |
| chat            | 1         |
| conversations   | 5         |
| export          | 1         |
| health (inline) | 1         |
| **TOTAL**       | **13**    |

---

*This document reflects the state of the `main` branch as of 2026-05-07.*
*All ground truth figures are Phase 0 locked values — see `data/audit/ground_truth.json`.*
*For figures registry (confirmed vs stale vs unverified), see `docs/figures-registry.md`.*



# Aequitas Platform — Master Reference Index

> **Source of truth:** Derived from live source code on `main`, 2026-05-07.
> Ground truth figures are Phase 0 locked values from `data/audit/ground_truth.json`.

---

## Document Structure

| Part   | File                                 | Contents                                                                                                                              |
| ------ | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| Part 1 | `AEQUITAS_MASTER_REFERENCE_PART1.md` | Platform overview, data pipeline, backend packages (core, ingestion, processing, analytics, intelligence, warehouse, validation, RAG) |
| Part 2 | `AEQUITAS_MASTER_REFERENCE_PART2.md` | API layer — all 13 endpoints, auth, routing, RAG chat service, Supabase schema                                                        |
| Part 3 | `AEQUITAS_MASTER_REFERENCE_PART3.md` | Frontend web app, chart components, hooks, test suite, known issues, notebook inventory, data traps                                   |

---

## Quick Reference

### Stack at a glance
- **Backend:** FastAPI 0.115 · Python 3.12 · DuckDB 1.1 (read-only warehouse)
- **LLM:** Gemini 2.5 Flash · FAISS (all-MiniLM-L6-v2) · SSE streaming
- **Frontend:** React 19 · Vite 6 · TypeScript 5.9 · Observable Plot · shadcn/ui · Tailwind v4
- **Auth:** Supabase JS v2 (JWT HS256)
- **Pipeline:** Click CLI (7 stages) · pandas · geopandas · scikit-learn · HDBSCAN · SHAP
- **Narrative engine:** InsightEngine (Jinja2 + evidence-gated rules — no LLM)

### API endpoints (13 total)

| Method | Path                               | Auth |
| ------ | ---------------------------------- | ---- |
| GET    | `/api/health`                      | None |
| GET    | `/api/overview`                    | None |
| GET    | `/api/sections`                    | None |
| GET    | `/api/lsoa/{table}`                | None |
| GET    | `/api/provenance/{metric_id}`      | None |
| GET    | `/api/metrics/ticker`              | None |
| GET    | `/api/export/{dimension}`          | None |
| POST   | `/api/chat`                        | JWT  |
| GET    | `/api/conversations`               | JWT  |
| POST   | `/api/conversations`               | JWT  |
| GET    | `/api/conversations/{id}/messages` | JWT  |
| POST   | `/api/conversations/{id}/messages` | JWT  |
| DELETE | `/api/conversations/{id}`          | JWT  |

### Pipeline stages

| Command                 | Stage | Output                                                                     |
| ----------------------- | ----- | -------------------------------------------------------------------------- |
| `aequitas ingest`       | 1     | `naptan_stops.parquet`, `bods_routes.parquet`, `master_lsoa_table.parquet` |
| `aequitas process`      | 2     | `route_geometries.parquet`, `lsoa_service_quality.parquet`                 |
| `aequitas analytics`    | 3     | Verifies Phase 0 audit Parquets                                            |
| `aequitas intelligence` | 4     | Narratives (via InsightEngine)                                             |
| `aequitas warehouse`    | 5     | `data/aequitas.duckdb`                                                     |
| `aequitas validate`     | 6     | `data/processed/validation_report.md`                                      |
| `aequitas rag`          | 7     | `data/faiss_index.bin` + `data/faiss_metadata.json`                        |
| `aequitas run`          | all   | All stages end-to-end                                                      |

### Section registry (51 sections)

See Part 1 §8.1 for the full table. Categories: A (coverage), B (service quality), C (route network), D (correlations), F (equity), G (ML), J (economic), BSA (Bus Services Act), PS (policy scenarios).

### Ground truth numbers (Phase 0 — locked)

| Metric                         | Value              |
| ------------------------------ | ------------------ |
| England active bus stops       | 274,719            |
| BODS unique routes             | 13,099             |
| England LSOAs                  | 33,755             |
| England population             | 56,490,056         |
| Gini coefficient (bus service) | 0.5741             |
| Palma ratio                    | 5.702              |
| Concentration Index            | +0.1358 (pro-rich) |
| Mean SQI                       | 65.4 / 100         |
| Evening isolated LSOAs         | 5,189 (15.4%)      |
| Sunday desert LSOAs            | 6,745 (20.0%)      |
| RF coverage model R²           | 0.472              |
| Top SHAP feature               | nocar_pct          |
| Triple-deprived LSOAs          | 612 (1.8%)         |

### Critical known issues

| #   | Issue                                         | Where to fix                               |
| --- | --------------------------------------------- | ------------------------------------------ |
| 1   | Box-violin `label` vs `group` schema mismatch | `BoxViolinChart.tsx` line 24               |
| 2   | Ticker queries wrong section IDs              | `api/routers/metrics.py` lines 42–49       |
| 3   | Precompute covers only 5 of 51 sections       | `warehouse/precompute.py` `_SECTIONS` list |
| 4   | Synchronous Gemini call blocks event loop     | `api/services/rag.py` `stream_gemini()`    |

### Test status (2026-05-07)

```
244 passed in 17m 24s
(excludes tests/rag and tests/api — require faiss-cpu and fastapi[testclient])
```
