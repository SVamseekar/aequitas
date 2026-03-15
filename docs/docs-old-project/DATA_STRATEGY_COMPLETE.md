# UK Bus Analytics: Complete Data Strategy & Gap Analysis

**Date:** 2025-11-02
**Purpose:** Comprehensive assessment of data availability, extraction strategy, and temporal analysis feasibility
**Status:** Production data pipeline operational, ready for enhancement

---

## Executive Summary

**Current State:**
- ✅ Spatial data infrastructure: **OPERATIONAL** (68k stops, 9 regions, full demographics)
- ⚠️ Route/schedule data: **IN RAW XML** (206 TransXChange files with trip schedules)
- ❌ Temporal data: **NOT COLLECTED** (single Oct 2025 snapshot only)

**Question Coverage:**
- **28/50 spatial questions** answerable NOW with existing processed data
- **11/50 spatial questions** require parsing raw TransXChange XML (2-3 hours work)
- **3/50 spatial questions** require simple data downloads (15 minutes)
- **6/50 spatial questions** missing critical data (hard/impossible to get)
- **11 temporal questions** require historical data collection (Phase 2)

**Recommended Priorities:**
1. **Week 1:** Parse TransXChange XML → Answer all 39 answerable spatial questions
2. **Week 2:** Download 3 missing datasets → Answer 3 more questions (42 total)
3. **Phase 2:** Collect historical data → Enable temporal analysis

---

## Part 1: Current Data Pipeline Architecture

### 1.1 Existing Pipeline Structure

```
data_pipeline/
├── 01_data_ingestion.py      # Downloads from BODS, ONS, NOMIS APIs
├── 02_data_processing.py     # Parses transport + merges demographics
├── 03_data_validation.py     # Quality checks
└── 04_descriptive_analytics.py  # Basic KPIs
```

**What the pipeline does:**
- Downloads bus stop/route data from Bus Open Data Service (BODS)
- Downloads demographics from ONS/NOMIS (population, IMD, unemployment, schools)
- Parses TransXChange XML to extract **stops only** (not routes/schedules)
- Merges all data at LSOA level
- Outputs: `stops_processed.csv` (68k rows) + `routes_processed.csv` (basic info only)

**What the pipeline does NOT do:**
- Extract trip schedules from TransXChange
- Extract route geometries/sequences
- Extract service frequency/headway data
- Collect historical/temporal data

---

## Part 2: Data Inventory by Question Category

### 2.1 CATEGORY A: Coverage & Accessibility (8 Questions)

| Q# | Question | Data Status | What We Have | What's Missing |
|----|----------|-------------|--------------|----------------|
| A1 | Regions with highest routes per capita | ✅ READY | stops + region + population | None |
| A2 | Regions with lowest stops per 1k residents | ✅ READY | stops + population | None |
| A3 | Stop density vs population density mismatch | ✅ READY | stops + population + LSOA area (calc) | None |
| A4 | Bus desert count (0 stops) | ✅ READY | stops by LSOA | None |
| A5 | Avg distance to nearest stop | ✅ READY | stops lat/lon + LSOA centroids | None |
| A6 | LAs with >50% residents >500m from stop | ⚠️ PARTIAL | stops + population | **LSOA boundary polygons** for buffer |
| A7 | Urban vs rural coverage comparison | ❌ MISSING | stops | **Rural-Urban classification** |
| A8 | High pop density + low service areas | ✅ READY | stops + population | None |

**Action Items:**
- **A6:** Download LSOA boundaries from ONS Geoportal → 5 min
- **A7:** Download Rural-Urban classification from ONS → 5 min

---

### 2.2 CATEGORY B: Service Frequency & Reliability (5 Spatial Questions)

| Q# | Question | Data Status | Location | Extraction Method |
|----|----------|-------------|----------|-------------------|
| B9 | Regions with highest trips per day | ⚠️ IN RAW | TransXChange `<VehicleJourney>` | Parse XML, count journeys by region |
| B10 | Lowest frequency relative to population | ⚠️ IN RAW | TransXChange `<VehicleJourney>` | Count journeys / population |
| B12 | Routes with late-night/early-morning service | ⚠️ IN RAW | TransXChange `<DepartureTime>` | Filter times <06:00 or >23:00 |
| B15 | Average headway by region | ⚠️ IN RAW | TransXChange `<DepartureTime>` | Calc time delta between consecutive trips |
| B16 | Rural vs urban frequency proportionality | ❌ MISSING | Need B9 + Rural-Urban data | Combine trip data + classification |

**What's in TransXChange XML:**
```xml
<VehicleJourney>
  <VehicleJourneyCode>464_20231001_1</VehicleJourneyCode>
  <ServiceRef>464</ServiceRef>
  <LineRef>464</LineRef>
  <DepartureTime>07:38:00</DepartureTime>
  <JourneyPatternRef>JP_464_OUTBOUND_1</JourneyPatternRef>
</VehicleJourney>
```

**Sample TransXChange File Statistics (from Abellio_London_5132.zip):**
- Services: 1 route
- Journey Patterns: 18 variants
- Vehicle Journeys: 230 trips
- Stop Points: 40 unique stops

**Across 206 files × ~200 trips avg = ~41,000 vehicle journeys total**

**Action Items:**
- Build `transxchange_schedule_extractor.py` to parse:
  - Route ID
  - Trip count per route
  - Departure times (for headway + operating hours)
  - Stop sequences (for route geometries)
- **Estimated effort:** 2-3 hours coding + 1 hour processing 206 files

---

### 2.3 CATEGORY C: Route Characteristics (7 Questions)

| Q# | Question | Data Status | What We Need from XML |
|----|----------|-------------|----------------------|
| C17 | Average route length per region | ⚠️ IN RAW | `<JourneyPatternSection>` stop sequences + distances |
| C18 | Routes with highest mileage per day | ⚠️ IN RAW | Route length × trip count |
| C19 | Overlapping routes (optimization) | ⚠️ IN RAW | Stop sequences for similarity analysis |
| C20 | Routes crossing multiple LAs | ⚠️ IN RAW | Route geometries + LA boundaries |
| C21 | High pop areas with few inter-city routes | ⚠️ IN RAW | Route geometries to detect region crossings |
| C22 | Routes serving schools | ✅ READY | stops + schools data (already have) |
| C23 | School hour vs work hour patterns | ⚠️ IN RAW | Departure times by time-of-day |

**TransXChange Route Geometry Structure:**
```xml
<JourneyPatternSection id="JPS_464_OUT_1">
  <JourneyPatternTimingLink id="JPTL_1">
    <From><StopPointRef>490000001A</StopPointRef></From>
    <To><StopPointRef>490000002B</StopPointRef></To>
    <RouteLinkRef>RL_464_1</RouteLinkRef>
    <RunTime>PT3M</RunTime>
    <Distance>1250</Distance>  <!-- meters -->
  </JourneyPatternTimingLink>
  <!-- ... more links -->
</JourneyPatternSection>
```

**What we can extract:**
- Stop-to-stop sequences (route shape)
- Distances between stops
- Running times
- Total route length = sum of all `<Distance>` tags

---

### 2.4 CATEGORY D: Socio-Economic Correlations (8 Questions)

| Q# | Question | Data Status | Data Source |
|----|----------|-------------|-------------|
| D24 | Correlation: deprivation ↔ stop density | ✅ READY | stops + IMD scores |
| D25 | Wealthier areas = better coverage? | ✅ READY | stops + IMD income deciles |
| D26 | Unemployment ↔ bus accessibility | ✅ READY | stops + unemployment_2024.csv |
| D27 | Elderly population ↔ stops | ✅ READY | stops + age_65_plus |
| D28 | Car ownership ↔ stop density | ❌ MISSING | **Need Census 2021 Table TS045** |
| D29 | Education levels ↔ bus service | ❌ MISSING | **Need Census 2021 Table TS067** |
| D30 | Business density ↔ connectivity | ✅ READY | stops + business_counts.csv |
| D31 | Health outcomes ↔ access | ✅ READY | stops + Health Deprivation (IMD) |

**Action Items:**
- Download Census 2021 car ownership data → 5 min
- Download Census 2021 education attainment → 5 min

---

### 2.5 CATEGORIES F-J: Equity, ML, Economic (Remaining Spatial Questions)

**Summary:**
- **16/20 questions fully answerable** with existing processed data
- **2/20 questions** need employment center POI data (complex, optional)
- **1/20 question** needs healthcare POI (NHS open data, easy)
- **1/20 question** impossible (gender mobility data doesn't exist)

---

## Part 3: Temporal Analysis - Full Assessment

### 3.1 Current Temporal Data Status

**What We Have:**
- ❌ **Single snapshot only:** October 2025
- ❌ **No historical data:** Previous months/years not collected
- ❌ **No trend data:** Cannot analyze growth, decline, seasonality

**What We Need for Temporal Analysis:**

#### CATEGORY E: Temporal & Trend Analysis (11 Questions Total)

| Q# | Question | Data Required | Availability | How to Get It |
|----|----------|---------------|--------------|---------------|
| E32 | Growth/decline trends over 3 years | 2022-2025 monthly snapshots | ⚠️ LIMITED | BODS historical archives (partial) |
| E33 | Seasonal ridership patterns | 12+ months of data | ❌ NOT PUBLIC | Need operator data (hard to get) |
| E34 | Service frequency changes over time | Historical schedules | ⚠️ POSSIBLE | BODS archives + Zenodo datasets |
| E35 | Route additions/cancellations tracking | Multi-year route lists | ⚠️ POSSIBLE | Compare BODS snapshots |
| E36 | Pandemic impact on service levels | 2019-2020-2021-2022 data | ✅ AVAILABLE | **Zenodo has 2021-2023 GTFS** |
| B11 | Weekend vs weekday frequency | Multi-day schedules | ⚠️ IN CURRENT | TransXChange has `<DaysOfWeek>` |
| B13 | Frequent cancellations/delays | Real-time vs scheduled | ❌ IMPOSSIBLE | Need SIRI-VM real-time feeds |
| B14 | Reliability: rich vs poor areas | Historical reliability | ❌ IMPOSSIBLE | Need operator performance data |
| F43 | Trend in equity gap over time | Multi-year demographics + stops | ⚠️ POSSIBLE | Historical BODS + Census |
| G48 | Demand forecasting | Historical ridership | ❌ IMPOSSIBLE | Operator-proprietary data |
| G49 | Predict service cuts | Historical route changes | ⚠️ POSSIBLE | Multi-year BODS snapshots |

---

### 3.2 Historical Data Sources

#### Option 1: Zenodo Academic Datasets (BEST OPTION)

**Source:** https://zenodo.org/communities/bus-open-data
**Data Available:**
- 2021-2023 GTFS snapshots (quarterly or annual)
- Some TransXChange archives
- Limited to major operators

**Pros:**
- ✅ Free, curated, citable
- ✅ Pre-processed GTFS format
- ✅ Covers pandemic period

**Cons:**
- ❌ Incomplete coverage (not all operators)
- ❌ Annual snapshots only (no monthly granularity)
- ❌ Last update may be 2023 (check freshness)

**How to integrate:**
```python
# Add to 01_data_ingestion.py
def download_historical_zenodo():
    """Download 2021-2023 GTFS from Zenodo"""
    zenodo_urls = {
        '2021': 'https://zenodo.org/record/XXXXX/files/uk_gtfs_2021.zip',
        '2022': 'https://zenodo.org/record/XXXXX/files/uk_gtfs_2022.zip',
        '2023': 'https://zenodo.org/record/XXXXX/files/uk_gtfs_2023.zip',
    }
    # Download and store in data/raw/historical/{year}/
```

---

#### Option 2: BODS Historical Archive (LIMITED)

**Source:** Bus Open Data Service archives
**Data Available:**
- Last 12 months of operator uploads (rolling window)
- Not guaranteed to be complete

**Pros:**
- ✅ Most recent data
- ✅ Same format as current pipeline

**Cons:**
- ❌ Only 12-month retention
- ❌ Operators can delete old uploads
- ❌ No pre-2024 data

**Feasibility:** **Can get 2024-2025 only**

---

#### Option 3: Manual Operator Requests (HIGH EFFORT)

**Source:** Direct from bus operators via FOI
**Feasibility:** ❌ **NOT RECOMMENDED**

**Pros:**
- Could get complete historical data

**Cons:**
- ❌ 3-6 month FOI response times
- ❌ Operators can refuse (commercial sensitivity)
- ❌ Data format varies by operator
- ❌ Would need to request from 50+ operators

---

### 3.3 Temporal Analysis Feasibility Matrix

| Analysis Type | Feasible? | Data Source | Effort | Temporal Range |
|---------------|-----------|-------------|--------|----------------|
| **Year-over-year trends** | ✅ YES | Zenodo 2021-2023 + Current 2025 | Medium (1-2 days) | 2021, 2022, 2023, 2025 |
| **Pandemic impact** | ✅ YES | Zenodo 2019-2023 | Medium | 2019-2023 |
| **Monthly seasonality** | ❌ NO | Not available publicly | N/A | N/A |
| **Weekly patterns** | ⚠️ PARTIAL | Current TransXChange has weekday/weekend | Low | Oct 2025 only |
| **Service reliability** | ❌ NO | Need real-time SIRI-VM (operator-only) | N/A | N/A |
| **Ridership trends** | ❌ NO | Operator-proprietary | N/A | N/A |

---

### 3.4 Recommended Temporal Data Collection Strategy

#### Phase 2A: Minimal Temporal (2 days effort)

**Download from Zenodo:**
1. 2021 UK GTFS snapshot
2. 2022 UK GTFS snapshot
3. 2023 UK GTFS snapshot

**Process:**
- Run existing `02_data_processing.py` on each year
- Create timestamped outputs: `stops_2021.csv`, `stops_2022.csv`, etc.
- Merge with historical demographics:
  - Population: Census 2021 (same for all years)
  - IMD: 2019 (same for all years)
  - Unemployment: Need to download 2021, 2022, 2023 from NOMIS
  - Schools: Use 2025 data for all years (schools change slowly)

**Answerable Temporal Questions:**
- ✅ E32: Growth/decline 2021 → 2025 (4-year trend)
- ✅ E34: Service frequency changes
- ✅ E35: Route additions/cancellations
- ✅ E36: Pandemic impact (compare 2021 vs 2023 vs 2025)
- ✅ F43: Equity gap trends
- ✅ G49: Predict service cuts (if 2021-2025 shows pattern)

**Still Unanswerable:**
- ❌ E33: Seasonal patterns (need monthly data)
- ❌ B13, B14: Reliability (need real-time data)
- ❌ G48: Demand forecasting (need ridership)

---

#### Phase 2B: Enhanced Temporal (1 week effort)

**Add to Phase 2A:**
- Download monthly BODS snapshots from last 12 months (Nov 2024 - Oct 2025)
- Enables monthly trend analysis for recent period

**Newly Answerable:**
- ⚠️ E33: Limited seasonality (12 months only, not multi-year)
- ✅ B11: Weekend vs weekday (already in current TransXChange)

---

## Part 4: Missing Data Acquisition Plan

### 4.1 Quick Wins (Total: 30 minutes)

#### Dataset 1: Rural-Urban Classification
- **Source:** https://www.gov.uk/government/statistics/rural-urban-classification
- **File:** "Rural Urban Classification 2011 of Lower Layer Super Output Areas in England and Wales.csv"
- **Size:** ~2 MB
- **Fields:** `lsoa_code`, `rural_urban_class` (e.g., "Urban major conurbation", "Rural village")
- **Integration:** Merge on `lsoa_code` in `02_data_processing.py`
- **Enables:** Questions A7, B16

```python
# Add to 02_data_processing.py
def merge_rural_urban_classification(stops_gdf, rural_urban_csv):
    ru = pd.read_csv(rural_urban_csv)
    return stops_gdf.merge(ru[['lsoa_code', 'rural_urban']], on='lsoa_code', how='left')
```

---

#### Dataset 2: LSOA Boundaries (GeoJSON)
- **Source:** https://geoportal.statistics.gov.uk/
- **Search:** "Lower Layer Super Output Areas (Dec 2021) Boundaries EW BGC"
- **Format:** GeoJSON or Shapefile
- **Size:** ~50 MB
- **Use:** 500m buffer analysis for question A6
- **Integration:** Load with GeoPandas

```python
import geopandas as gpd

def calculate_coverage_buffers():
    lsoa_boundaries = gpd.read_file('data/raw/boundaries/lsoa_2021.geojson')
    stops_gdf = gpd.GeoDataFrame(stops, geometry=gpd.points_from_xy(stops.longitude, stops.latitude))

    # 500m buffer around each stop
    stops_gdf['buffer'] = stops_gdf.geometry.buffer(500)  # meters

    # Spatial join: which LSOAs are covered?
    coverage = gpd.sjoin(lsoa_boundaries, stops_gdf, predicate='intersects')
```

---

#### Dataset 3: Car Ownership (Census 2021)
- **Source:** https://www.nomisweb.co.uk/
- **Table:** TS045 - Car or van availability
- **Geography:** LSOA (2021)
- **Download:** Bulk CSV (all England LSOAs)
- **Fields:** `lsoa_code`, `no_cars`, `1_car`, `2+_cars`, `total_households`
- **Integration:** Merge in `02_data_processing.py`
- **Enables:** Question D28

---

### 4.2 Medium Effort (2-4 hours each)

#### Dataset 4: Education Attainment (Census 2021)
- **Source:** NOMIS Census Table TS067
- **Effort:** 10 min download + 30 min cleaning
- **Enables:** Question D29

#### Dataset 5: NHS Healthcare POI
- **Source:** https://digital.nhs.uk/services/organisation-data-service
- **Data:** GP practices + hospitals with postcodes
- **Effort:** 1 hour (download + geocode postcodes to lat/lon)
- **Enables:** Question G47

---

### 4.3 Hard/Optional (Not Recommended)

#### Employment Centers
- **Challenge:** No official "employment center" dataset
- **Workaround:** Use business counts as proxy (already have)
- **Verdict:** Skip F39, I56, J60 (3 questions)

#### Accessibility Features
- **Challenge:** NaPTAN has fields but 80% missing data
- **Verdict:** Skip H51 (1 question)

#### Gender Mobility
- **Challenge:** Doesn't exist at LSOA level
- **Verdict:** Skip F42 (1 question)

---

## Part 5: Implementation Roadmap

### Week 1: Complete Spatial Analysis (39 → 42 questions)

**Day 1-2: Build TransXChange Schedule Parser**
```python
# Create: utils/transxchange_schedule_extractor.py

class TransXChangeScheduleExtractor:
    """Extract route geometries, trips, and schedules from XML"""

    def extract_route_data(self, xml_path):
        # Parse XML
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ns = {'txc': 'http://www.transxchange.org.uk/'}

        # Extract routes
        routes = []
        for service in root.findall('.//txc:Service', ns):
            route_id = service.find('.//txc:LineName', ns).text

            # Get journey patterns (route shapes)
            patterns = service.findall('.//txc:JourneyPattern', ns)
            for pattern in patterns:
                sections = pattern.findall('.//txc:JourneyPatternSectionRefs', ns)
                # Build stop sequence from sections

            # Get trips
            journeys = service.findall('.//txc:VehicleJourney', ns)
            trips = []
            for journey in journeys:
                trip = {
                    'route_id': route_id,
                    'departure_time': journey.find('.//txc:DepartureTime', ns).text,
                    'journey_pattern': journey.find('.//txc:JourneyPatternRef', ns).text
                }
                trips.append(trip)

        return routes, trips
```

**Day 3: Process All 206 Files**
```bash
python utils/transxchange_schedule_extractor.py --input data/raw/regions/ --output data/processed/schedules/
```

**Outputs:**
- `routes_detailed.csv` (route_id, line_name, stop_sequence, total_length_m)
- `trips.csv` (trip_id, route_id, departure_time, day_of_week)
- `route_geometries.geojson` (route shapes for mapping)

**Day 4-5: Download Missing Datasets + Re-run Analysis**
1. Download Rural-Urban classification (5 min)
2. Download LSOA boundaries (5 min)
3. Download car ownership (5 min)
4. Modify `02_data_processing.py` to merge new data (1 hour)
5. Re-run pipeline: `python data_pipeline/02_data_processing.py` (2 hours processing)

**Result:** 42/50 spatial questions now answerable

---

### Week 2: Visualization & Analysis Scripts

**Create analysis notebooks for each category:**
```
analysis/
├── category_a_coverage.ipynb          # 8 questions
├── category_b_frequency.ipynb         # 5 questions
├── category_c_routes.ipynb            # 7 questions
├── category_d_socioeconomic.ipynb     # 8 questions
├── category_f_equity.ipynb            # 6 questions
├── category_g_ml_insights.ipynb       # 5 questions
├── category_h_accessibility.ipynb     # 4 questions
└── category_ij_economic.ipynb         # 7 questions
```

---

### Phase 2 (Optional): Temporal Analysis

**Week 3: Historical Data Collection**
1. Search Zenodo for UK bus GTFS datasets (2021-2023)
2. Download and validate data quality
3. Download historical unemployment (NOMIS 2021-2023)
4. Run `02_data_processing.py` for each historical year

**Week 4: Temporal Analysis**
1. Create comparative datasets (2021 vs 2025)
2. Calculate growth rates, service changes
3. Build temporal visualization notebooks
4. Answer 6 temporal questions (E32, E34, E35, E36, F43, G49)

**Result:** 48/61 total questions answerable (79%)

---

## Part 6: Final Question Coverage Summary

### After Week 1 (Spatial Complete):

| Category | Total Q's | Answered | % |
|----------|-----------|----------|---|
| A: Coverage | 8 | 8 | 100% |
| B: Frequency | 5 | 4 | 80% |
| C: Routes | 7 | 7 | 100% |
| D: Socio-Economic | 8 | 7 | 88% |
| F: Equity | 6 | 5 | 83% |
| G: Advanced ML | 5 | 4 | 80% |
| H: Accessibility | 4 | 3 | 75% |
| I+J: Economic | 7 | 6 | 86% |
| **Spatial Total** | **50** | **44** | **88%** |

### After Phase 2 (Temporal Added):

| Category | Total Q's | Answered | % |
|----------|-----------|----------|---|
| E: Temporal | 11 | 6 | 55% |
| **Grand Total** | **61** | **50** | **82%** |

---

## Part 7: Data Pipeline Enhancement Plan

### New Script 1: `utils/transxchange_schedule_extractor.py`

**Purpose:** Extract route/schedule data from TransXChange XML
**Inputs:** 206 .zip files (actually XML)
**Outputs:**
- `routes_detailed.csv` (route geometries, lengths)
- `trips_schedule.csv` (all trips with times)
- `route_stop_sequences.csv` (stop order per route)

**Integration Point:** Called by `02_data_processing.py` after stop extraction

---

### New Script 2: `data_pipeline/01b_download_auxiliary_data.py`

**Purpose:** Automate download of missing Census/ONS datasets
**Downloads:**
1. Rural-Urban classification
2. LSOA boundaries
3. Car ownership (Census TS045)
4. Education (Census TS067) - optional
5. NHS POI data - optional

**Run Once:** Before main pipeline

---

### Modified Script: `data_pipeline/02_data_processing.py`

**Add functions:**
```python
def merge_rural_urban(stops_gdf):
    """Merge rural-urban classification"""

def calculate_buffer_coverage(stops_gdf, lsoa_boundaries):
    """Calculate 500m buffer coverage for A6"""

def merge_car_ownership(stops_gdf):
    """Merge Census car ownership data"""
```

---

### New Script 3: `data_pipeline/05_temporal_processing.py` (Phase 2)

**Purpose:** Process historical datasets
**Inputs:** Zenodo GTFS archives (2021-2023)
**Outputs:** Time-series datasets for trend analysis

---

## Part 8: Consulting Frameworks Data Mapping

### McKinsey/BCG/Deloitte Analytics Covered:

✅ **Network Optimization:** Questions C17-C21 (route overlap, efficiency)
✅ **Equity Analysis:** Questions F37-F42 (IMD-based coverage gaps)
✅ **BCR Calculations:** Questions J58-J61 (economic impact modeling)
✅ **Demographic Segmentation:** Category D (8 correlations)
✅ **Predictive Analytics:** Questions G43-G49 (ML-based insights)
⚠️ **Demand Forecasting:** Limited (no ridership data)
❌ **Real-time Operations:** Not possible (no SIRI-VM access)

---

## Appendix A: Data Source URLs

1. **Rural-Urban Classification:** https://www.gov.uk/government/statistics/rural-urban-classification
2. **LSOA Boundaries:** https://geoportal.statistics.gov.uk/ (search "LSOA 2021 Boundaries")
3. **Census Tables (NOMIS):** https://www.nomisweb.co.uk/sources/census_2021_bulk
4. **NHS POI Data:** https://digital.nhs.uk/services/organisation-data-service/export-data-files/csv-downloads/gp-and-gp-practice-related-data
5. **Zenodo Bus Data:** https://zenodo.org/communities/bus-open-data (search "UK GTFS")

---

## Appendix B: Estimated Processing Times

| Task | Time | Output |
|------|------|--------|
| Build TransXChange parser | 2-3 hours | Script ready |
| Process 206 XML files | 1-2 hours | Routes + trips CSVs |
| Download 3 missing datasets | 15 min | 3 CSV files |
| Modify processing pipeline | 1 hour | Enhanced merger |
| Re-run full pipeline | 2 hours | Updated stops_processed.csv |
| **Total (Week 1)** | **6-8 hours** | **42 questions answerable** |
| Download Zenodo historical | 1 hour | 2021-2023 GTFS |
| Process historical data | 6 hours | 3 years × 2h each |
| Build temporal analysis | 4 hours | Trend notebooks |
| **Total (Phase 2)** | **11 hours** | **50 questions answerable** |

---

## Conclusion

**Current Capability:** 28/50 spatial questions (56%)
**Week 1 Target:** 44/50 spatial questions (88%)
**Phase 2 Target:** 50/61 total questions (82%)

**Critical Path:**
1. ✅ Spatial data: Already collected, needs enhanced parsing
2. ⚠️ Route/schedule data: In raw XML, needs 6-8 hours extraction
3. ❌ Temporal data: Not collected, Phase 2 required (11 hours)

**Recommendation:** Prioritize Week 1 extraction → Deliver 88% spatial coverage → Evaluate if Phase 2 temporal worth the effort based on stakeholder needs.
