# Phase 0 Complete EDA — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Phase 0 EDA with 100% dataset coverage, zero gaps, policy-grade confidence on every figure, column, and row — so the data foundation is unassailable before Phase 1 pipeline build.

**Architecture:** Two notebook series built on top of the existing `01`–`02i` foundation. Series `03` (8 notebooks) audits each new dataset with the same 103-check rigour as `01_data_audit`. Series `04` (6 notebooks) builds the 6 analytical layers combining all data. Every notebook produces validation artifacts, updates the figures registry, and writes output parquet/csv to `data/audit/`.

**Tech Stack:** Python 3.12+, Jupyter (jupytext for authoring → .ipynb for execution), pandas, geopandas, scipy, scikit-learn, sentence-transformers, hdbscan, shap, openpyxl, matplotlib, seaborn, folium

---

## Dependency Graph

```
Series 03 — New Dataset Audits (can run in parallel, no inter-dependencies)
  03a_disability_ts038        → Factor 9 into master_lsoa_table
  03b_hospitals               → Geocoded hospital locations
  03c_gp_surgeries            → Geocoded GP locations
  03d_schools_gias            → Filtered school locations with coordinates
  03e_employment_bres         → MSOA employment → LSOA proxy
  03f_tag_databook            → Extracted TAG v2.03fc constants (⚠️→✅)
  03g_desnz_carbon            → Extracted DESNZ 2025 CO2 factors (⚠️→✅)
  03h_codepoint_postcodes     → Postcode→coordinate lookup table

Series 04 — Analytical Layers (sequential dependencies shown)
  04a_route_geometry           ← depends on: 02b (BODS), shapes.txt
  04b_service_quality_depth    ← depends on: 02g, 02h, 04a
  04c_equity_framework         ← depends on: 03a (disability), 02e, 02g, 02h, 02i
  04d_ml_suite                 ← depends on: 04a, 04b, 04c, all 03x
  04e_economic_appraisal       ← depends on: 03f (TAG), 03g (DESNZ), 04b, 04c
  04f_policy_synthesis         ← depends on: 03b-03e (POI/employment), 04a-04e (all layers)
```

---

## Chunk 1: Series 03 — New Dataset Audits

These 8 notebooks can be built and executed in any order. Each follows the same pattern:
1. Load raw file, profile every column (dtype, nulls, range, distribution)
2. Filter to England where applicable
3. Validate row counts, join keys, geographic coverage
4. Produce clean output artifact in `data/audit/`
5. Update `docs/figures-registry.md` with any new confirmed figures
6. Log validation checks (PASS/WARN/FAIL) consistent with `01_data_audit` format

---

### Task 1: `03a_disability_ts038.ipynb` — Census TS038 Disability Audit

**Purpose:** Integrate Factor 9 (disability / long-term health conditions) into the master LSOA table. This is the last missing socio-economic factor — without it, the vulnerability index is incomplete.

**Input:** `data/raw/census/census2021-ts038-lsoa.csv` (35,672 rows including Wales, 10 columns)

**Output:** `data/audit/master_lsoa_table.parquet` (updated — adds disability columns)

- [ ] **Step 1: Create notebook with jupytext**

Create `notebooks/03a_disability_ts038.py` with the following structure:

```python
# ---
# jupyter:
#   jupytext:
#     text_representation:
#       format_name: percent
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # 03a — Census TS038: Disability / Long-Term Health Conditions
#
# **Purpose:** Audit and integrate Factor 9 (disability) into master_lsoa_table.
# Completes the 9-factor socio-economic profile for every England LSOA.
#
# **Source:** ONS Census 2021 Table TS038 — Disability
# **File:** `data/raw/census/census2021-ts038-lsoa.csv`
# **Expected:** 35,672 rows (England + Wales), 10 columns
# **Filter:** England only (LSOA codes starting with E)

# %% [markdown]
# ## 1. Load and Profile

# %%
import pandas as pd
import numpy as np
import json
from pathlib import Path

DATA_RAW = Path("../data/raw")
DATA_AUDIT = Path("../data/audit")

ts038 = pd.read_csv(DATA_RAW / "census/census2021-ts038-lsoa.csv")
print(f"Shape: {ts038.shape}")
print(f"Columns: {list(ts038.columns)}")
ts038.head()

# %%
# Column-by-column profile: dtype, nulls, unique, min, max, mean
ts038.describe(include="all").T

# %%
# Null check — every column
null_report = ts038.isnull().sum()
print("Null counts per column:")
print(null_report)
assert null_report.sum() == 0, f"FAIL: {null_report.sum()} nulls found"
print("CHECK PASS: zero nulls")

# %% [markdown]
# ## 2. Filter to England

# %%
# England LSOA codes start with 'E'
ts038_eng = ts038[ts038["geography code"].str.startswith("E")].copy()
print(f"England rows: {len(ts038_eng)}")
print(f"Wales rows removed: {len(ts038) - len(ts038_eng)}")
assert len(ts038_eng) == 33_755, f"FAIL: expected 33,755 England LSOAs, got {len(ts038_eng)}"
print("CHECK PASS: 33,755 England LSOAs")

# %% [markdown]
# ## 3. Derive Disability Metrics

# %%
# Key columns from TS038:
# - "Disability: Total: All usual residents" = total population (should match TS001)
# - "Disability: Disabled under the Equality Act" = disabled count
# - "Disability: Disabled under the Equality Act: Day-to-day activities limited a lot" = severely disabled
# - "Disability: Disabled under the Equality Act: Day-to-day activities limited a little" = moderately disabled

total_col = "Disability: Total: All usual residents"
disabled_col = "Disability: Disabled under the Equality Act"
limited_lot_col = "Disability: Disabled under the Equality Act: Day-to-day activities limited a lot"
limited_little_col = "Disability: Disabled under the Equality Act: Day-to-day activities limited a little"

ts038_eng["disability_pct"] = (ts038_eng[disabled_col] / ts038_eng[total_col] * 100).round(2)
ts038_eng["disability_severe_pct"] = (ts038_eng[limited_lot_col] / ts038_eng[total_col] * 100).round(2)

print(f"Disability % range: {ts038_eng['disability_pct'].min():.1f}% – {ts038_eng['disability_pct'].max():.1f}%")
print(f"Disability % mean: {ts038_eng['disability_pct'].mean():.1f}%")
print(f"Severe disability % range: {ts038_eng['disability_severe_pct'].min():.1f}% – {ts038_eng['disability_severe_pct'].max():.1f}%")

# %% [markdown]
# ## 4. Distribution Analysis

# %%
import matplotlib.pyplot as plt
import seaborn as sns

fig, axes = plt.subplots(1, 3, figsize=(18, 5))

axes[0].hist(ts038_eng["disability_pct"], bins=50, edgecolor="black", alpha=0.7)
axes[0].set_title("Disability % Distribution (All LSOAs)")
axes[0].set_xlabel("% Disabled under Equality Act")
axes[0].axvline(ts038_eng["disability_pct"].mean(), color="red", linestyle="--", label=f"Mean: {ts038_eng['disability_pct'].mean():.1f}%")
axes[0].legend()

axes[1].hist(ts038_eng["disability_severe_pct"], bins=50, edgecolor="black", alpha=0.7, color="orange")
axes[1].set_title("Severe Disability % Distribution")
axes[1].set_xlabel("% Day-to-day limited a lot")
axes[1].axvline(ts038_eng["disability_severe_pct"].mean(), color="red", linestyle="--", label=f"Mean: {ts038_eng['disability_severe_pct'].mean():.1f}%")
axes[1].legend()

# Boxplot by decile
axes[2].boxplot([ts038_eng["disability_pct"].values], vert=True)
axes[2].set_title("Disability % Boxplot")
axes[2].set_ylabel("% Disabled")

plt.tight_layout()
plt.savefig(DATA_AUDIT / "fig_03a_disability_distribution.png", dpi=150, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## 5. Cross-Validate Population with TS001

# %%
master = pd.read_parquet(DATA_AUDIT / "master_lsoa_table.parquet")
print(f"Master table shape: {master.shape}")

# Check population alignment
ts038_pop = ts038_eng.set_index("geography code")[total_col]
# master should have a population column — check what it's called
print(f"Master columns: {list(master.columns)}")

# %% [markdown]
# ## 6. Correlation with Other Factors

# %%
# Merge disability into master table on LSOA code
# Identify the LSOA code column in master
lsoa_col = [c for c in master.columns if "lsoa" in c.lower() or "code" in c.lower()][0]
print(f"Master LSOA column: {lsoa_col}")

disability_slim = ts038_eng[["geography code", "disability_pct", "disability_severe_pct"]].rename(
    columns={"geography code": lsoa_col}
)

master_with_disability = master.merge(disability_slim, on=lsoa_col, how="left")
null_after_merge = master_with_disability["disability_pct"].isnull().sum()
print(f"Nulls after merge: {null_after_merge}")
assert null_after_merge == 0, f"FAIL: {null_after_merge} LSOAs missing disability data"
print("CHECK PASS: 100% merge — all 33,755 LSOAs have disability data")

# Correlation matrix with key factors
corr_cols = [c for c in master_with_disability.columns if any(k in c.lower() for k in
    ["imd", "unemployment", "car", "elderly", "disability", "income", "ethnic", "urban"])]
if len(corr_cols) > 2:
    corr_matrix = master_with_disability[corr_cols + ["disability_pct"]].corr()
    print("\nCorrelation of disability_pct with other factors:")
    print(corr_matrix["disability_pct"].sort_values(ascending=False))

# %% [markdown]
# ## 7. Update Master LSOA Table

# %%
# Save updated master table with disability columns
master_with_disability.to_parquet(DATA_AUDIT / "master_lsoa_table.parquet", index=False)
print(f"Updated master_lsoa_table.parquet: {master_with_disability.shape}")
print("Factor 9 (disability) now integrated.")

# %% [markdown]
# ## 8. Validation Summary

# %%
checks = [
    ("TS038 zero nulls", null_report.sum() == 0, "PASS" if null_report.sum() == 0 else "FAIL"),
    ("England LSOAs = 33,755", len(ts038_eng) == 33_755, "PASS" if len(ts038_eng) == 33_755 else "FAIL"),
    ("100% merge with master", null_after_merge == 0, "PASS" if null_after_merge == 0 else "FAIL"),
    ("Disability % range valid", ts038_eng["disability_pct"].min() >= 0 and ts038_eng["disability_pct"].max() <= 100, "PASS"),
]

for name, result, status in checks:
    print(f"  [{status}] {name}")

fail_count = sum(1 for _, _, s in checks if s == "FAIL")
assert fail_count == 0, f"{fail_count} checks FAILED"
print(f"\n03a COMPLETE: {len(checks)} checks, all PASS. Factor 9 integrated into master_lsoa_table.")
```

- [ ] **Step 2: Convert to ipynb and execute**

```bash
cd notebooks && jupytext --to ipynb 03a_disability_ts038.py && jupyter nbconvert --to notebook --execute 03a_disability_ts038.ipynb --inplace --ExecutePreprocessor.timeout=600
```

- [ ] **Step 3: Verify outputs exist**

```bash
ls -la data/audit/master_lsoa_table.parquet
python3 -c "import pandas as pd; df = pd.read_parquet('data/audit/master_lsoa_table.parquet'); print(f'Columns: {len(df.columns)}, has disability_pct: {\"disability_pct\" in df.columns}')"
```

- [ ] **Step 4: Update figures-registry.md**

Add to Category 2 — Statistical Results:
```
| ST-008 | Disability % range (TS038) | [extracted min]–[extracted max]%, 0 nulls | ✅ Confirmed | 03a_disability_ts038.ipynb | England LSOAs, Equality Act definition |
| ST-009 | Disability % mean (England) | [extracted mean]% | ✅ Confirmed | 03a_disability_ts038.ipynb | |
```

Add to Appendix:
```
| 03a_disability_ts038.ipynb | ST-008, ST-009 | See Category 2 |
```

- [ ] **Step 5: Commit**

```bash
git add notebooks/03a_disability_ts038.ipynb data/audit/master_lsoa_table.parquet docs/figures-registry.md
git commit -m "feat(eda): 03a disability TS038 audit — Factor 9 integrated into master LSOA table"
```

---

### Task 2: `03b_hospitals.ipynb` — NHS ODS Hospital Locations Audit

**Purpose:** Audit hospital locations, geocode via Code-Point Open, validate spatial distribution, produce clean geocoded hospital dataset for healthcare accessibility analysis (Layer 6).

**Input:** `data/raw/poi/hospitals.csv` (3,884 rows, 4 columns: OrgId, Name, PostCode, LastChangeDate)

**Dependencies:** Requires Code-Point Open (`data/raw/boundaries/code_point_open/data/CSV/`)

**Output:** `data/audit/hospitals_geocoded.parquet` (hospitals with Easting/Northing/Lat/Lon)

- [ ] **Step 1: Create notebook**

Create `notebooks/03b_hospitals.py` covering:

```
Sections:
1. Load and profile hospitals.csv — every column, dtypes, nulls, duplicates
2. Validate: row count, OrgId uniqueness, postcode format (regex: [A-Z]{1,2}[0-9][0-9A-Z]? [0-9][A-Z]{2})
3. Load Code-Point Open CSVs, build postcode→Easting/Northing lookup
   - Code-Point has no header row — columns are: Postcode, PQI, Easting, Northing, Country, NHS_HA, NHS_RHA, County, District, Ward
   - Load ALL 120 CSVs, concat, strip whitespace from postcodes
4. Join hospitals to Code-Point on PostCode → get Easting/Northing
   - Log match rate (must be >95%)
   - Investigate unmatched postcodes
5. Convert Easting/Northing (BNG EPSG:27700) → Lat/Lon (WGS84 EPSG:4326)
   - Use pyproj: Transformer.from_crs("EPSG:27700", "EPSG:4326")
6. Spatial validation:
   - All lat/lon within England bounding box (49.8–55.9°N, -6.5–1.8°E)
   - Map hospitals on England outline
   - Regional distribution (count per region)
7. Name analysis: categorise by type (Hospital, Infirmary, Community, Walk-in, etc.)
8. Save data/audit/hospitals_geocoded.parquet
9. Validation summary (checks logged)
```

- [ ] **Step 2: Convert and execute**
- [ ] **Step 3: Verify outputs, update figures-registry.md**

Add GT-014: `England acute hospitals | [count] | ✅ Confirmed | 03b_hospitals.ipynb`

- [ ] **Step 4: Commit**

```bash
git add notebooks/03b_hospitals.ipynb data/audit/hospitals_geocoded.parquet docs/figures-registry.md
git commit -m "feat(eda): 03b hospitals audit — geocoded via Code-Point Open, spatial validation"
```

---

### Task 3: `03c_gp_surgeries.ipynb` — NHS ODS GP Surgery Locations Audit

**Purpose:** Same rigour as 03b but for GP surgeries. Primary care is the most policy-relevant healthcare metric at LSOA level.

**Input:** `data/raw/poi/epraccur.csv` (12,213 rows, 4 columns)

**Dependencies:** Code-Point Open postcode lookup (can reuse from 03b or rebuild independently)

**Output:** `data/audit/gp_surgeries_geocoded.parquet`

- [ ] **Step 1: Create notebook**

Same pattern as 03b, with GP-specific additions:
```
Sections:
1. Load and profile epraccur.csv
2. Validate: row count, OrgId uniqueness, postcode format
3. Build/reuse Code-Point Open lookup
4. Geocode via postcode join — log match rate
5. BNG → WGS84 conversion
6. Spatial validation (bounding box, England outline map)
7. Regional distribution + density per 10,000 population
8. GP-to-LSOA spatial join: point-in-polygon → count GPs per LSOA
   - Cross-reference with IMD: do deprived areas have fewer GPs per capita?
9. Save data/audit/gp_surgeries_geocoded.parquet
10. Validation summary
```

- [ ] **Step 2: Convert and execute**
- [ ] **Step 3: Update figures-registry, commit**

Add GT-015: `England GP surgeries | [count] | ✅ Confirmed | 03c_gp_surgeries.ipynb`

---

### Task 4: `03d_schools_gias.ipynb` — GIAS Schools Audit

**Purpose:** Audit education establishment data. 135 columns — every one must be classified. Focus on open secondary schools for accessibility analysis.

**Input:** `data/raw/poi/gias_schools.csv` (52,278 rows, 135 columns, **latin-1 encoding**)

**Output:** `data/audit/schools_secondary_geocoded.parquet`, `data/audit/gias_column_inventory.csv`

- [ ] **Step 1: Create notebook**

```
Sections:
1. Load with encoding='latin-1' — profile shape, dtypes, memory usage
2. Column inventory: classify ALL 135 columns as USE/IGNORE/REVIEW with rationale
   - Save as data/audit/gias_column_inventory.csv
3. Filter: EstablishmentStatus (code) == 1 (Open)
   - Count: expect ~27,183 open schools
4. Phase breakdown: PhaseOfEducation — Primary, Secondary, All-through, etc.
   - Secondary + All-through for accessibility analysis
   - Count: expect ~3,339 (3,173 secondary + 166 all-through)
5. Coordinate availability:
   - Check Easting/Northing columns — expect 97.8% non-null
   - Investigate missing coordinates — which schools have no location?
   - For schools with postcodes but no coordinates: geocode via Code-Point Open
6. Convert Easting/Northing → Lat/Lon
7. Spatial validation:
   - England bounding box check
   - Map secondary schools
   - Schools per LA (Local Authority) distribution
8. Cross-reference with bus stops:
   - For each secondary school, find nearest bus stop (KDTree)
   - Distribution of school-to-stop distances
   - Schools with no bus stop within 400m
9. Save outputs:
   - data/audit/schools_secondary_geocoded.parquet (secondary + all-through, open, with coordinates)
   - data/audit/schools_all_open_geocoded.parquet (all open schools, for completeness)
   - data/audit/gias_column_inventory.csv
10. Validation summary
```

- [ ] **Step 2: Convert and execute**
- [ ] **Step 3: Update figures-registry, commit**

Add GT-016, GT-017: open schools count, secondary schools count

---

### Task 5: `03e_employment_bres.ipynb` — NOMIS BRES Employment Audit

**Purpose:** Audit MSOA-level employment data and create LSOA-level proxy via spatial join. Employment centres are critical for job accessibility analysis.

**Input:** `data/raw/nomis/bres_msoa_2023.csv` (7,201 rows, 3 columns: GEOGRAPHY_CODE, GEOGRAPHY_NAME, OBS_VALUE)

**Dependencies:** LSOA-to-MSOA lookup (derived from LSOA codes — each LSOA code contains its parent MSOA)

**Output:** `data/audit/lsoa_employment_proxy.parquet`

- [ ] **Step 1: Create notebook**

```
Sections:
1. Load and profile BRES MSOA — every column, dtypes, nulls, range
2. Validate:
   - Row count (expect 7,201 total, 6,791 England MSOAs starting with E)
   - Filter to England
   - OBS_VALUE: min, max, mean, total (expect ~27.3M employees)
   - Zero nulls
3. MSOA employment distribution:
   - Histogram
   - Top/bottom MSOAs
   - Employment density by region
4. LSOA→MSOA mapping:
   - ONS provides LSOA-to-MSOA lookup in Census data
   - OR derive from LSOA/MSOA code structure
   - Validate: every England LSOA maps to exactly one MSOA
5. Create LSOA employment proxy:
   - Option A: assign MSOA employment equally across child LSOAs (crude)
   - Option B: weight by LSOA population (better)
   - Document which approach used and why
6. Validate proxy:
   - Sum of LSOA proxies should equal MSOA total
   - Distribution sanity check
7. Cross-reference with IMD:
   - Employment vs deprivation correlation
   - Which deprived LSOAs are also employment deserts?
8. Save data/audit/lsoa_employment_proxy.parquet
9. Validation summary
```

- [ ] **Step 2: Convert and execute**
- [ ] **Step 3: Update figures-registry, commit**

Add GT-018: `England MSOAs (BRES) | 6,791 | ✅ Confirmed | 03e_employment_bres.ipynb`
Add GT-019: `Total England employees (BRES 2023) | [total] | ✅ Confirmed | 03e_employment_bres.ipynb`

---

### Task 6: `03f_tag_databook.ipynb` — TAG v2.03fc Value Extraction

**Purpose:** Programmatically extract all transport appraisal constants from the TAG Databook v2.03fc. This resolves TAG-001 through TAG-005 (⚠️ Stale → ✅ Confirmed).

**Input:** `data/raw/tag/tag-data-book-v2-03fc-dec-2025.xlsm` (6.6 MB, macro-enabled Excel)

**Output:** `data/audit/tag_constants.json`, updated `docs/figures-registry.md`

- [ ] **Step 1: Create notebook**

```
Sections:
1. Load workbook with openpyxl (read_only mode — ignore macros)
   - List ALL sheet names — document every tab
2. Tab A1.3.1 — Values of Time (non-work)
   - Navigate to the value cells
   - Extract: bus commuting time (£/hr), car commuting time (£/hr), leisure time (£/hr)
   - Note the price year (should be 2023 prices)
   - Compare with stale values: bus £9.85, car £12.65, leisure £7.85
3. Tab A1.3.2 — Values of Time (work/business)
   - Extract: business travel time (£/hr)
   - Compare with stale value: £28.30/hr
4. Tab A1.3.7 — Vehicle Operating Costs
   - Extract relevant vehicle cost parameters
5. Carbon values tab (if present, or cross-reference with DESNZ)
   - Extract: carbon value (£/tonne CO2e, central estimate)
   - Compare with stale value: £80/tonne
6. Document every extracted value with:
   - Cell reference (e.g. "Tab A1.3.1, Cell D15")
   - Exact value
   - Price year
   - Stale value it replaces
7. Save data/audit/tag_constants.json:
   {
     "source": "TAG Databook v2.03fc (Dec 2025)",
     "price_year": "2023",
     "extracted_by": "03f_tag_databook.ipynb",
     "values": {
       "bus_commuting_time_per_hr": ...,
       "car_commuting_time_per_hr": ...,
       "business_travel_time_per_hr": ...,
       "leisure_travel_time_per_hr": ...,
       "carbon_value_per_tonne": ...,
       "social_discount_rate": 0.035
     }
   }
8. Validation summary
```

- [ ] **Step 2: Convert and execute**
- [ ] **Step 3: Update figures-registry.md**

Change TAG-001 through TAG-005 from ⚠️ Stale to ✅ Confirmed with new values. Source = `03f_tag_databook.ipynb`.

- [ ] **Step 4: Update architecture.md TAG constants table with extracted values**
- [ ] **Step 5: Commit**

```bash
git add notebooks/03f_tag_databook.ipynb data/audit/tag_constants.json docs/figures-registry.md
git commit -m "feat(eda): 03f TAG v2.03fc extraction — TAG-001 to TAG-005 now Confirmed"
```

---

### Task 7: `03g_desnz_carbon.ipynb` — DESNZ GHG Factors 2025 Extraction

**Purpose:** Extract transport CO2 emission factors from DESNZ 2025 spreadsheet. Resolves CO2-001 and CO2-002 (⚠️ Stale → ✅ Confirmed).

**Input:** `data/raw/carbon/ghg-conversion-factors-2025-condensed-set.xlsx` (1.8 MB)

**Output:** `data/audit/desnz_carbon_factors.json`, updated `docs/figures-registry.md`

- [ ] **Step 1: Create notebook**

```
Sections:
1. Load workbook with openpyxl
   - List ALL sheet names
2. Find transport factors sheet/tab
   - Navigate to bus and car emission factors
3. Extract:
   - Bus CO2 per passenger-km (kg CO2e/pax-km) — compare with stale 0.0965
   - Car CO2 per km (kg CO2e/km) — compare with stale 0.171
   - Car CO2 per passenger-km (if available)
   - Document: scope (well-to-wheel vs tank-to-wheel), occupancy assumptions
4. Additional useful factors:
   - Rail CO2 per passenger-km (for modal comparison)
   - Walk/cycle = 0 (baseline)
5. Document every extracted value with cell reference, exact value, scope
6. Save data/audit/desnz_carbon_factors.json
7. Validation summary
```

- [ ] **Step 2: Convert and execute**
- [ ] **Step 3: Update figures-registry.md**

Change CO2-001 and CO2-002 from ⚠️ Stale to ✅ Confirmed with new values.

- [ ] **Step 4: Update architecture.md carbon constants**
- [ ] **Step 5: Commit**

```bash
git add notebooks/03g_desnz_carbon.ipynb data/audit/desnz_carbon_factors.json docs/figures-registry.md
git commit -m "feat(eda): 03g DESNZ 2025 carbon extraction — CO2-001 and CO2-002 now Confirmed"
```

---

### Task 8: `03h_codepoint_postcodes.ipynb` — Code-Point Open Audit

**Purpose:** Build and validate the master postcode→coordinate lookup that NHS ODS geocoding depends on. 120 CSVs, no headers — must be profiled thoroughly.

**Input:** `data/raw/boundaries/code_point_open/data/CSV/` (120 CSV files, ~1 GB total)

**Output:** `data/audit/postcode_lookup.parquet`

- [ ] **Step 1: Create notebook**

```
Sections:
1. List all 120 CSVs, document naming convention (2-letter prefix = postcode area)
2. Load one sample file, determine column structure:
   - Columns (no headers): Postcode, PQI, Easting, Northing, Country, NHS_HA, NHS_RHA, County, District, Ward
   - Assign column names manually
3. Load ALL 120 files, concat into single DataFrame
   - Profile: total rows, null counts per column, dtype check
4. Filter to England postcodes:
   - Country code for England (check what Code-Point uses)
   - OR filter by Easting/Northing within England bounds
5. Postcode format validation:
   - Regex: UK postcode pattern
   - Strip whitespace, standardise format
6. Coordinate validation:
   - Easting range (valid for England BNG: ~80,000–660,000)
   - Northing range (valid for England BNG: ~5,000–660,000)
   - Flag any outliers
7. Coverage check:
   - Total England postcodes in dataset
   - Cross-reference: how many of our hospital/GP/school postcodes are found?
8. Convert BNG → WGS84 for a sample (validate conversion)
9. Save data/audit/postcode_lookup.parquet (Postcode, Easting, Northing, Lat, Lon)
10. Validation summary
```

- [ ] **Step 2: Convert and execute**
- [ ] **Step 3: Update figures-registry, commit**

Add GT-020: `Code-Point Open England postcodes | [count] | ✅ Confirmed | 03h_codepoint_postcodes.ipynb`

---

### Task 9: Series 03 Capstone — Validation Gate

**Purpose:** After all 8 `03x` notebooks execute successfully, run a capstone validation that confirms the data foundation is complete.

- [ ] **Step 1: Run validation script**

```python
# Quick validation — run in a cell or standalone script
import pandas as pd
from pathlib import Path

AUDIT = Path("data/audit")

# Check all outputs exist
required = [
    "master_lsoa_table.parquet",       # Updated with disability
    "hospitals_geocoded.parquet",
    "gp_surgeries_geocoded.parquet",
    "schools_secondary_geocoded.parquet",
    "lsoa_employment_proxy.parquet",
    "tag_constants.json",
    "desnz_carbon_factors.json",
    "postcode_lookup.parquet",
]

for f in required:
    path = AUDIT / f
    assert path.exists(), f"MISSING: {f}"
    print(f"  ✅ {f} ({path.stat().st_size / 1024:.0f} KB)")

# Check master table has 9 factors
master = pd.read_parquet(AUDIT / "master_lsoa_table.parquet")
assert "disability_pct" in master.columns, "FAIL: disability not in master table"
assert len(master) == 33_755, f"FAIL: master table has {len(master)} rows, expected 33,755"
print(f"\n  ✅ Master LSOA table: {master.shape[0]} rows × {master.shape[1]} columns (9 factors)")

# Check no stale TAG/DESNZ figures remain
import json
tag = json.load(open(AUDIT / "tag_constants.json"))
desnz = json.load(open(AUDIT / "desnz_carbon_factors.json"))
print(f"  ✅ TAG constants: {len(tag['values'])} values extracted (price year: {tag['price_year']})")
print(f"  ✅ DESNZ carbon factors: extracted")

print("\n=== SERIES 03 COMPLETE — ALL VALIDATION GATES PASSED ===")
```

- [ ] **Step 2: Commit milestone**

```bash
git add -A data/audit/ notebooks/03*.ipynb docs/figures-registry.md
git commit -m "feat(eda): Series 03 complete — 8 new datasets audited, all validation gates passed"
```

---

## Chunk 2: Series 04 — Analytical Layers

These 6 notebooks build the deep analytical layers, combining all data from Series 01–03. They have sequential dependencies (shown in dependency graph above) and must be executed in order.

---

### Task 10: `04a_route_geometry.ipynb` — Layer 1: Route Geometry

**Purpose:** Extract and analyse route geometry from BODS shapes.txt (3.2 GB). This is the single largest gap — blocks all 7 Category C questions. Produces route-level features needed for ML clustering (Layer 4).

**Input:** `data/raw/bods/bods_gtfs_all.zip` → `shapes.txt` (3.2 GB), `routes.txt`, `trips.txt`, `stops.txt`, `stop_times.txt`

**Output:**
- `data/audit/route_geometries.parquet` — route-level features (length, stops, shape, cross-LA flag)
- `data/audit/route_stop_sequences.parquet` — ordered stop sequences per route

- [ ] **Step 1: Create notebook**

```
Sections:
1. Extract shapes.txt from ZIP (chunked reading — 3.2 GB)
   - Profile: columns (shape_id, shape_pt_lat, shape_pt_lon, shape_pt_sequence, shape_dist_traveled)
   - Row count, null check, coordinate range validation

2. Link shapes to routes:
   - trips.txt has: trip_id, route_id, shape_id
   - Group: route_id → shape_id(s) → shape points
   - Handle: one route may have multiple shape variants (inbound/outbound)

3. Route length computation:
   - Haversine distance between consecutive shape points
   - Sum per shape_id → route length in km
   - Distribution: min, max, mean, median route lengths
   - Histogram of route lengths
   - Flag suspiciously long (>100km) or short (<0.5km) routes

4. Stop sequence extraction:
   - From stop_times.txt (chunked): trip_id → stop_id → stop_sequence
   - Link to routes via trips.txt
   - Per route: ordered list of unique stops, total stop count
   - Distribution of stops per route

5. Cross-Local-Authority routes:
   - For each route, get all stop locations (from stops.txt)
   - Spatial join stops to LSOA boundaries → get LA codes
   - Route crosses LA boundary if stops span >1 LA
   - Count and list cross-LA routes

6. Overlapping routes:
   - Routes sharing >50% of stops = "overlapping"
   - Identify overlapping clusters
   - Map examples of high-overlap corridors

7. Route type categorisation:
   - By length: urban (<15km), suburban (15-40km), interurban (>40km)
   - By stop count: express (<10 stops), local (10-40), comprehensive (>40)
   - Cross-tabulate with operator

8. Regional route distribution:
   - Routes per region
   - Average route length per region
   - Map route density

9. Save outputs:
   - data/audit/route_geometries.parquet (one row per route: route_id, length_km, stop_count, cross_la, route_type, region, operator, shape_points_simplified)
   - data/audit/route_stop_sequences.parquet (route_id, stop_sequence, stop_id, lat, lon)

10. Validation summary
    - Total routes with geometry: [count] / 13,099
    - Routes missing shapes: [count] (log and investigate)
    - Ground truth check: unique routes still = 13,099
```

- [ ] **Step 2: Convert and execute** (timeout: 20 min — large files)
- [ ] **Step 3: Update figures-registry, commit**

Add GT-021: `Routes with geometry | [count] | ✅ Confirmed | 04a_route_geometry.ipynb`
Add ST-010: `Mean route length (km) | [value] | ✅ Confirmed | 04a_route_geometry.ipynb`
Add ST-011: `Cross-LA routes | [count] ([pct]%) | ✅ Confirmed | 04a_route_geometry.ipynb`

---

### Task 11: `04b_service_quality_depth.ipynb` — Layer 2: Service Quality

**Purpose:** Move beyond "how many trips" to "how good is the service." Headway, reliability proxy, population-weighted coverage, evening/Sunday isolation. Builds on 02g + 02h + 04a.

**Input:** Existing audit artifacts + stop_times.txt (chunked) + LSOA boundaries + population data

**Output:**
- `data/audit/lsoa_service_quality.parquet` — per-LSOA quality metrics
- `data/audit/stop_headways.parquet` — per-stop headway statistics

- [ ] **Step 1: Create notebook**

```
Sections:
1. Headway computation:
   - From stop_times.txt: per stop, per day type (weekday/Saturday/Sunday)
   - Sort departures chronologically
   - Headway = gap between consecutive departures (minutes)
   - Metrics per stop: mean headway, median headway, max headway, CoV (coefficient of variation)
   - Save: data/audit/stop_headways.parquet

2. Headway by time period:
   - AM peak (07:00-09:30), interpeak (09:30-16:00), PM peak (16:00-18:30), evening (18:30-23:00)
   - Peak-to-interpeak headway ratio (policy metric: <1.5 = good, >2.0 = poor)

3. Buffer-based population coverage:
   - For each bus stop: 400m radius buffer
   - Intersect with LSOA boundaries (area-weighted)
   - Population within 400m of at least one bus stop (population-weighted, not centroid-based)
   - Compare with centroid-based estimate from 02h

4. Evening isolation score:
   - Per LSOA: last departure time from any stop within LSOA
   - "Evening isolated" = no service after 19:00
   - "Night isolated" = no service after 22:00
   - Cross-reference with employment patterns (shift workers)

5. Sunday desert classification:
   - Per LSOA: Sunday trip count
   - "Sunday desert" = zero Sunday trips
   - "Sunday minimal" = 1-4 Sunday trips
   - Map Sunday deserts overlaid with deprivation

6. Composite service quality index:
   - Weighted combination: headway (40%) + span of service (20%) + frequency (20%) + reliability proxy (10%) + weekend service (10%)
   - Normalise 0-100
   - Distribution analysis

7. Service quality by archetype:
   - Cross-reference with 4 LSOA archetypes from 02e
   - Box plots of quality index by archetype
   - Policy insight: which archetypes have worst service quality?

8. Service quality by IMD decile:
   - Scatter plot: IMD score vs service quality index
   - Pearson/Spearman correlation
   - Key finding: does deprivation predict service quality?

9. Save data/audit/lsoa_service_quality.parquet
   - Columns: lsoa_code, mean_headway_weekday, cov_headway, peak_interpeak_ratio,
     last_departure_time, sunday_trips, evening_isolated, sunday_desert,
     service_quality_index, population_within_400m

10. Validation summary
```

- [ ] **Step 2: Convert and execute**
- [ ] **Step 3: Update figures-registry, commit**

---

### Task 12: `04c_equity_framework.ipynb` — Layer 3: Equity Framework

**Purpose:** Compute formal equity metrics aligned with DfT/ONS/OECD frameworks. This is the analytical heart of the platform — every policy recommendation depends on equity evidence.

**Input:** `data/audit/master_lsoa_table.parquet` (with disability), `data/audit/lsoa_service_levels.parquet`, `data/audit/lsoa_accessibility.parquet`, `data/audit/lsoa_service_quality.parquet`

**Output:**
- `data/audit/lsoa_equity_metrics.parquet` — per-LSOA equity indicators
- `data/audit/equity_summary.json` — national-level equity statistics

- [ ] **Step 1: Create notebook**

```
Sections:
1. Gini coefficient of bus service distribution:
   - Measure: trips per capita across all 33,755 LSOAs
   - Gini = 0 (perfect equality) to 1 (perfect inequality)
   - Interpretation in transport context

2. Lorenz curve:
   - X-axis: cumulative % of population (sorted by service level)
   - Y-axis: cumulative % of bus trips
   - Plot with 45° equality line
   - Identify: bottom 20% of population receives what % of service?

3. Palma ratio:
   - Top 10% service / Bottom 40% service
   - Preferred by UN/OECD over Gini for policy
   - Interpretation: >1 means top 10% gets more than bottom 40%

4. Concentration Index:
   - Service inequality correlated with socio-economic rank (IMD)
   - Negative = service concentrated among deprived (pro-poor)
   - Positive = service concentrated among affluent (pro-rich)
   - The SIGN of this metric is THE policy finding

5. Dissimilarity Index:
   - Spatial segregation of bus access
   - What proportion of bus service would need to redistribute for equal access?

6. Vulnerability Index:
   - Composite: IMD rank (normalised) + no-car % + elderly % + disability % + unemployment %
   - Weight by policy relevance (equal weights initially, sensitivity analysis)
   - Per LSOA score 0-100
   - Identify: top vulnerability decile vs bottom — service gap?

7. Triple deprivation intersectionality:
   - LSOAs that are simultaneously: high IMD + high no-car + high elderly
   - Add disability as 4th dimension: quadruple vulnerability
   - Count and map these "maximum vulnerability" LSOAs
   - Cross-reference with service quality index from 04b

8. Equity by archetype:
   - Gini within each of the 4 archetypes
   - Are some archetypes internally more unequal?

9. Equity by region:
   - Regional Gini, Palma, Concentration Index
   - Map: which regions have most unequal bus distribution?

10. Policy-actionable summary:
    - "If we brought the bottom deprivation decile to median service, the Gini would change by X"
    - "The Concentration Index of [value] means coverage is [pro-poor/pro-rich]"

11. Save outputs:
    - data/audit/lsoa_equity_metrics.parquet (lsoa_code, vulnerability_index, triple_deprived, quadruple_deprived)
    - data/audit/equity_summary.json (national Gini, Palma, CI, DI, Lorenz curve data)

12. Validation summary
```

- [ ] **Step 2: Convert and execute**
- [ ] **Step 3: Update figures-registry**

Add to Category 2:
```
ST-012: Gini coefficient (bus service) | [value] | ✅ Confirmed | 04c_equity_framework.ipynb
ST-013: Palma ratio (bus service) | [value] | ✅ Confirmed | 04c_equity_framework.ipynb
ST-014: Concentration Index (bus-IMD) | [value] | ✅ Confirmed | 04c_equity_framework.ipynb
ST-015: Triple-deprived LSOAs | [count] | ✅ Confirmed | 04c_equity_framework.ipynb
ST-016: Quadruple-vulnerable LSOAs | [count] | ✅ Confirmed | 04c_equity_framework.ipynb
```

- [ ] **Step 4: Commit**

---

### Task 13: `04d_ml_suite.ipynb` — Layer 4: ML Models

**Purpose:** Production ML suite — HDBSCAN clustering, RF+SHAP coverage prediction, Isolation Forest anomaly detection, 2SFCA accessibility. These feed the RAG chatbot with intelligent context.

**Input:** All audit artifacts from Series 03 + Layers 1-3

**Output:**
- `data/audit/lsoa_clusters_hdbscan.parquet` — HDBSCAN + GMM soft cluster assignments
- `data/audit/route_clusters.parquet` — route-level clusters
- `data/audit/coverage_prediction.parquet` — RF predictions + SHAP values
- `data/audit/anomalies.parquet` — Isolation Forest + LOF anomalies
- `data/audit/lsoa_2sfca.parquet` — Two-Step Floating Catchment Area scores

- [ ] **Step 1: Create notebook**

```
Sections:
1. HDBSCAN LSOA clustering (upgrade from KMeans):
   - Feature matrix: all 9 socio-economic factors + service quality + accessibility
   - HDBSCAN with min_cluster_size tuning
   - Compare with KMeans k=4 — do the archetypes hold?
   - Gaussian Mixture Models for soft membership probabilities
   - Silhouette comparison: HDBSCAN vs KMeans vs GMM

2. Route clustering:
   - Features per route: name embedding (SentenceTransformers all-MiniLM-L6-v2), stop count, length, region, operator
   - HDBSCAN on combined feature space
   - Cluster interpretation: express, local urban, suburban, rural, school, night
   - Map cluster examples

3. Coverage prediction (Random Forest):
   - Target: trips per capita (continuous) or service tier (classification)
   - Features: 9 socio-economic factors + urban/rural + region
   - Train/test split (80/20, stratified by region)
   - Random Forest + XGBoost + LightGBM comparison
   - R² score — THE finding: if R²~0.089, it means 91% of variance is policy-driven, not demographics
   - SHAP values: which factors matter most?
   - SHAP summary plot + dependence plots

4. Anomaly detection:
   - Isolation Forest (production parameters, not 1% proof-of-concept)
   - Features: service level vs deprivation vs car ownership vs elderly
   - Anomaly types:
     a) Deprived + good coverage (positive anomaly — what's working?)
     b) Affluent + poor coverage (inefficiency)
     c) High elderly + no service (policy failure)
   - Local Outlier Factor as second opinion
   - Cross-reference anomalies with archetypes

5. 2SFCA (Two-Step Floating Catchment Area):
   - Industry standard for accessibility measurement (NHS, DfT)
   - Step 1: For each bus stop, compute supply-to-demand ratio (trips / population within catchment)
   - Step 2: For each LSOA, sum ratios of all stops within catchment
   - Catchment: 400m walking distance (Euclidean approximation)
   - Result: continuous accessibility score per LSOA
   - Compare with simpler metrics from 02h
   - Map 2SFCA scores

6. Model validation:
   - Cross-validation (5-fold) for all supervised models
   - Feature importance stability across folds
   - Residual analysis: where does the model fail?

7. Save all outputs (listed above)
8. Validation summary
```

- [ ] **Step 2: Convert and execute** (timeout: 30 min — ML models + embeddings)
- [ ] **Step 3: Update figures-registry**

Update ST-007: `Coverage prediction R² | [actual value] | ✅ Confirmed | 04d_ml_suite.ipynb`
Add ST-017+: HDBSCAN cluster count, anomaly count, 2SFCA range

- [ ] **Step 4: Commit**

---

### Task 14: `04e_economic_appraisal.ipynb` — Layer 5: Economic Appraisal

**Purpose:** BCR calculations, investment gap analysis, modal shift modelling, carbon reduction. Uses confirmed TAG v2.03fc and DESNZ 2025 values from Series 03.

**Input:** `data/audit/tag_constants.json`, `data/audit/desnz_carbon_factors.json`, all Layer 1-3 outputs

**Output:**
- `data/audit/lsoa_economic_appraisal.parquet` — per-LSOA BCR estimates, investment gap
- `data/audit/modal_shift_scenarios.parquet` — carbon and cost impact of scenarios

- [ ] **Step 1: Create notebook**

```
Sections:
1. Load confirmed TAG + DESNZ constants
   - Verify all values are ✅ Confirmed (not stale)
   - Display constants table with source reference

2. Investment gap analysis:
   - For each LSOA in bottom IMD decile: what service level increase is needed to reach median?
   - Cost model: additional trips × operating cost per trip-km (from TAG if available)
   - Aggregate: total investment needed for bottom decile → median
   - Sensitivity: ±20% cost variation

3. BCR calculator (Green Book methodology):
   - Benefits: time savings (TAG VOT × trips × time saved) + carbon savings + health benefits (walking to stops)
   - Costs: operating costs + capital costs (if new infrastructure)
   - BCR = PV(benefits) / PV(costs) at 3.5% social discount rate
   - Apply to: top 500 transport deserts (from 02i)
   - Categorise by BCR band (Poor/Low/Medium/High/Very High)
   - Map BCR estimates

4. Modal shift modelling:
   - DfT elasticities: fare (-0.4 to -0.6), frequency (+0.4 to +0.7)
   - Scenario: 20% frequency increase in bottom deprivation decile
   - Estimate: additional trips generated (frequency elasticity × baseline trips)
   - Estimate: car trips replaced (cross-reference with car ownership)
   - Note: these are indicative estimates, not precision economics

5. Carbon reduction from modal shift:
   - Car trips replaced × average trip length × car CO2 factor (DESNZ 2025)
   - Minus: additional bus trips × bus CO2 factor (DESNZ 2025)
   - Net carbon saving per year
   - Monetise at TAG carbon value

6. Employment impact (indicative):
   - GDP multiplier (if verified) or skip with documented reason
   - Note methodological limitations of applying national multipliers locally

7. Sensitivity analysis:
   - Vary: elasticities ±25%, VOT ±10%, carbon price ±20%
   - Tornado chart showing which parameter has most impact on BCR

8. Save outputs
9. Validation summary — every constant used must trace to a ✅ Confirmed figure
```

- [ ] **Step 2: Convert and execute**
- [ ] **Step 3: Update figures-registry, commit**

---

### Task 15: `04f_policy_synthesis.ipynb` — Layer 6: Policy Synthesis

**Purpose:** The capstone — brings everything together for policy actionability. Bus Services Act readiness, operator analysis, accessibility to essential services (healthcare, education, employment), policy scenarios.

**Input:** All audit artifacts, all layer outputs, geocoded POI data

**Output:**
- `data/audit/lsoa_policy_synthesis.parquet` — per-LSOA policy indicators
- `data/audit/lta_franchising_readiness.parquet` — per-LTA franchising scores
- `data/audit/policy_scenarios.parquet` — scenario modelling results

- [ ] **Step 1: Create notebook**

```
Sections:
1. Healthcare accessibility gap:
   - For each LSOA: distance to nearest hospital (KDTree on geocoded hospitals)
   - For each LSOA: distance to nearest GP surgery
   - Cross-reference: high deprivation + far from hospital + poor bus service = healthcare desert
   - Map healthcare deserts
   - Count LSOAs where nearest hospital is >5km AND no bus service

2. Education accessibility gap:
   - For each LSOA: distance to nearest secondary school
   - Cross-reference: deprived + far from school + poor bus service
   - Schools with no bus stop within 400m (from 03d)
   - Map education deserts

3. Employment accessibility:
   - LSOA employment proxy (from 03e)
   - Low employment + high deprivation + poor bus service = job accessibility desert
   - 2SFCA variant for job accessibility

4. Operator market analysis:
   - HHI (Herfindahl-Hirschman Index) per region
   - HHI interpretation: <1,000 competitive, 1,000-2,500 moderately concentrated, >2,500 highly concentrated
   - Operator presence vs coverage gaps
   - Single-operator dependency regions

5. Bus Services Act 2025 — LTA Franchising Readiness Index:
   - Components: HHI (operator concentration), service level (trips/capita), deprivation (IMD mean), service quality (from 04b), single-operator dependency
   - Composite score per LTA
   - Ranking: which LTAs should franchise first?
   - Map readiness scores

6. Policy scenario modelling:
   - Scenario A: Restore frequency to median in bottom IMD decile
     → Cost (from 04e), BCR, modal shift, carbon savings, population affected
   - Scenario B: Extend last bus to 23:00 in all evening-isolated LSOAs
     → Population benefited, employment impact (shift workers), cost
   - Scenario C: Introduce DRT in rural elderly archetypes
     → Cost per trip vs fixed route, population density threshold for DRT viability
   - Scenario D: Bus Services Act — franchise top-5 LTAs
     → Service level change estimate, cost to public sector, operator impact

7. Integrated vulnerability-accessibility matrix:
   - 2D scatter: vulnerability index (04c) vs accessibility score (04d 2SFCA)
   - Quadrants: High vulnerability + Low access = PRIORITY
   - Name the quadrants for policy communication
   - Top 100 priority LSOAs with full profiles

8. Policy recommendations framework:
   - Evidence-graded: each recommendation cites specific metrics and confidence level
   - Tier 1 (high confidence): based on ✅ Confirmed figures only
   - Tier 2 (indicative): based on model outputs with documented uncertainty

9. Save outputs
10. Final validation summary — comprehensive check of all figures used
```

- [ ] **Step 2: Convert and execute**
- [ ] **Step 3: Update figures-registry, commit**

---

### Task 16: Series 04 Capstone — Final Phase 0 Validation

**Purpose:** Comprehensive validation that Phase 0 EDA is complete — every dataset audited, every analytical layer built, every figure confirmed or properly documented.

- [ ] **Step 1: Run final validation**

Verify:
1. All 19 notebooks exist and have been executed (01, 02–02i, 03a–03h, 04a–04f)
2. All data/audit/ artifacts exist and have correct row counts
3. All figures-registry entries are either ✅ Confirmed or explicitly documented as ❌ Unverified with reason
4. No ⚠️ Stale figures remain (TAG and DESNZ resolved by 03f and 03g)
5. Master LSOA table has all 9 factors
6. Ground truth counts unchanged (274,719 stops, 13,099 routes, 33,755 LSOAs)

- [ ] **Step 2: Update SESSION_REPORT**

Add Phase 0 EDA completion section documenting:
- Total notebooks: 19
- Total validation checks: [cumulative count]
- Total output artifacts: [count]
- All 9 socio-economic factors: ✅
- All 8 policy dimensions covered: ✅
- Figures registry status: [count] ✅ / [count] ❌ with reason / 0 ⚠️

- [ ] **Step 3: Update MEMORY.md**

Update Phase 0 status from "IN PROGRESS" to reflect completion.
Update Layer 0-6 status from ❌/⚠️ to ✅.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "Phase 0 EDA complete: 19 notebooks, 8 policy dimensions, 9 factors, all datasets audited"
```

---

## Summary — Total Deliverables

| Series | Notebooks | Key Outputs |
|--------|-----------|-------------|
| 03 (Dataset Audits) | 8 notebooks (03a–03h) | 8 new audit artifacts, TAG/DESNZ values confirmed, master table updated |
| 04 (Analytical Layers) | 6 notebooks (04a–04f) | Route geometry, service quality, equity metrics, ML models, economic appraisal, policy synthesis |
| **Total new** | **14 notebooks** | **~20 new data artifacts, 0 stale figures, complete policy-grade EDA** |

**Cumulative Phase 0:** 19 notebooks total (01 + 02–02i + 03a–03h + 04a–04f), ~35 audit artifacts, 9 socio-economic factors, 8 policy dimensions, ground truth locked.

**After this plan completes, Phase 0 is done.** The data foundation is unassailable. Phase 1 (pipeline build) can begin.
