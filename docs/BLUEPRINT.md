# Aequitas: Clean-Sheet Technical Blueprint

**Version:** 2.0
**Date:** 2026-03-10
**Classification:** Internal Engineering Reference
**Premise:** How a senior engineer would build a UK bus transport policy intelligence platform from nothing — driven purely by the problem, the audience, and the constraints.

---

## Table of Contents

1. [The Problem](#1-the-problem)
2. [The Audience](#2-the-audience)
3. [The Constraints](#3-the-constraints)
4. [Analytical Questions This Platform Must Answer](#4-analytical-questions-this-platform-must-answer)
5. [Data Sources: What Exists in the UK Government Ecosystem](#5-data-sources-what-exists-in-the-uk-government-ecosystem)
6. [System Architecture: Design Decisions From First Principles](#6-system-architecture-design-decisions-from-first-principles)
7. [Phase Zero: Know the Data Before Writing a Line of Code](#7-phase-zero-know-the-data-before-writing-a-line-of-code)
8. [Data Layer: Ingestion, Processing, Warehouse](#8-data-layer-ingestion-processing-warehouse)
9. [Intelligence Layer: How Numbers Become Narratives](#9-intelligence-layer-how-numbers-become-narratives)
10. [Presentation Layer: What Policy Makers Actually See](#10-presentation-layer-what-policy-makers-actually-see)
11. [Conversational Layer: RAG Chatbot for Policy Q&A](#11-conversational-layer-rag-chatbot-for-policy-qa)
12. [Deployment & Operations](#12-deployment--operations)
13. [Quality System: How Trust Is Built and Maintained](#13-quality-system-how-trust-is-built-and-maintained)
14. [Build Sequence](#14-build-sequence)
15. [Technology Choices](#15-technology-choices)
16. [What Success Looks Like](#16-what-success-looks-like)

---

## 1. The Problem

UK bus transport policy decisions affecting tens of millions of commuters are made without accessible, integrated analytical tooling.

The data exists. The UK government publishes:
- Every bus stop location in the country (NaPTAN)
- Every bus route and timetable (BODS)
- Population, demographics, deprivation scores at neighbourhood level (ONS Census, IMD)

But these datasets live across different government APIs, in incompatible formats, with no single platform that cross-references bus coverage with demographic need. A transport authority planner who wants to answer "which deprived communities have the worst bus access?" must manually download data from 4+ government portals, clean it, join it, analyse it, and write the narrative — a process that takes weeks and produces non-reproducible results.

**What's needed:** A platform that does this work once, correctly, reproducibly, and presents the results in a form that policy makers can use directly in business cases, investment bids, and Parliamentary briefings.

---

## 2. The Audience

### Primary: Policy Makers & Transport Planners

- **Department for Transport (DfT) officials** writing National Bus Strategy updates
- **Local Transport Authority (LTA) planners** building investment cases for bus service improvements
- **Combined Authority transport teams** (e.g., Transport for Greater Manchester, West Yorkshire Combined Authority) doing regional benchmarking

**What they need:** Numbers they can cite in HM Treasury business cases. Narratives that pass scrutiny from Government Analytical Service (GAS) standards. BCR calculations that follow TAG (Transport Appraisal Guidance) methodology.

**What kills credibility:** A single inconsistent number across two pages. A correlation reported without a p-value. An investment recommendation without a BCR. A national average that doesn't account for population weighting. Any of these, once spotted, permanently discredits the platform. Policy stakeholders do not give second chances.

### Secondary: Academic Researchers

- Transport geography researchers
- Public policy PhD students
- Think tanks (e.g., Campaign for Better Transport, Transport Focus)

**What they need:** Downloadable data, transparent methodology, reproducible results.

### Tertiary: Industry

- Bus operators (First Group, Stagecoach, Arriva, Go-Ahead) doing market analysis
- Transport consultants (Steer, Mott MacDonald, Arup) benchmarking regions

---

## 3. The Constraints

| Constraint | Implication |
|-----------|-------------|
| **Zero budget** | Free-tier everything: hosting, LLM APIs, vector stores, CI/CD |
| **Solo developer** | No separate frontend/backend teams. Single Python codebase. |
| **Must be HM Treasury compliant** | TAG 2024 time values, Green Book discount rates, approved BCR bands |
| **Must be auditable** | Every number on screen must trace to its source data through a documented formula |
| **Monthly data refresh** | NaPTAN and BODS update monthly; platform must ingest updates without manual intervention |
| **Policy-maker audience** | No technical jargon in output. Professional consulting tone. Quantified, not qualitative. |
| **England only** | Scotland, Wales, NI have different transport governance. BODS coverage is England-only. |

---

## 4. Analytical Questions This Platform Must Answer

These are the questions that transport planners actually ask. They define what the platform must compute, not the other way around.

Category labels (A, B, C, D, F, G, J) are non-sequential by design — letters E (Temporal Patterns), H (Network Topology), and I (Predictive Modelling) are reserved for future analytical categories that require additional data sources (e.g., real-time SIRI-VM feeds for temporal analysis, GTFS shapes for network topology). The 7 categories below are implementable with currently available government open data.

### Category A: Coverage & Accessibility
> *"Which regions have the most and fewest bus routes per capita? Where are the coverage gaps?"*

- **A1** How does bus route density (routes per 100,000 population) vary across England's 9 regions?
- **A2** How does bus stop density (stops per 1,000 population) vary across regions?
- **A3** What proportion of the population lives within walking distance (400m urban, 800m rural) of a bus stop?
- **A4** How equitably is bus coverage distributed within each region? (Gini coefficient across neighbourhoods)
- **A5** Where are the "service deserts" — neighbourhoods with population but no bus stops?
- **A6** What is the urban vs rural coverage gap, and how does it vary by region?
- **A7** What investment would be needed to bring every region up to the national average? (TAG 2024 BCR)
- **A8** Can we predict a neighbourhood's bus coverage from its demographics? (ML model)

### Category B: Service Quality
> *"Are buses frequent enough? Do services run at useful times?"*

- **B1** What is the average service frequency by region (trips per day)?
- **B2** How do operating hours (first/last service) vary across regions?
- **B3** Is there a weekend service penalty? How much does frequency drop on Saturdays/Sundays?
- **B4** Which routes are the most and least frequent?
- **B5** How does service frequency relate to deprivation? (Do deprived areas get fewer buses?)

### Category C: Route Characteristics
> *"What do the bus routes look like? How long, how many stops, what types?"*

- **C1** What is the distribution of route lengths across regions?
- **C2** How many stops does a typical route serve?
- **C3** What is the operator landscape? (market concentration, HHI index)
- **C4** How do route characteristics differ between urban and rural areas?
- **C5** Are there economies of scale? (Does route length correlate with frequency?)
- **C6** What route archetypes exist? (ML clustering: urban commuter, rural connector, etc.)
- **C7** How does the network topology look? (Hub-and-spoke vs mesh)

### Category D: Socio-Economic Correlations
> *"Does bus service go where it's needed most?"*

- **D1** Does bus coverage correlate with deprivation (IMD score)?
- **D2** Does bus coverage correlate with unemployment rates?
- **D3** Does bus coverage correlate with car ownership (or lack thereof)?
- **D4** Does bus coverage correlate with elderly population share?
- **D5** Does bus coverage correlate with income levels?
- **D6** Is there a "transport poverty" cluster — areas with high need and low service?
- **D7** What is the interaction between deprivation and urban/rural classification?
- **D8** Multi-variate: which demographic factors best predict bus coverage?

### Category F: Equity & Social Inclusion
> *"Is bus service distributed fairly?"*

- **F1** What is the Gini coefficient for bus stop distribution by population?
- **F2** What is the disparity ratio between most-deprived and least-deprived neighbourhoods?
- **F3** How does bus access vary by ethnic composition of neighbourhoods?
- **F4** What is the gender-adjusted accessibility gap? (proxy: childcare/school access)
- **F5** What is the rural accessibility penalty compared to urban?
- **F6** Which regions have the most equitable distribution?

### Category G: ML Insights
> *"What patterns can machine learning reveal that manual analysis misses?"*

- **G1** Route clustering: what natural groupings of bus services exist?
- **G2** Anomaly detection: which neighbourhoods have surprisingly poor (or good) service?
- **G3** Coverage prediction: can we predict where service gaps will emerge?
- **G4** Feature importance: what demographic factors drive coverage differences?
- **G5** Scenario modelling: what would happen if we added X routes to region Y?

### Category J: Economic Impact & BCR
> *"What is bus transport worth to the economy? Where should we invest?"*

- **J1** What is the economic value of current bus services per region? (TAG 2024 methodology)
- **J2** What is the BCR for closing coverage gaps in underserved regions?
- **J3** What is the carbon reduction value of bus vs car mode shift?
- **J4** Regional investment prioritisation: rank regions by BCR for new investment

---

## 5. Data Sources: What Exists in the UK Government Ecosystem

### 5.1 Bus Infrastructure Data

#### NaPTAN (National Public Transport Access Nodes)
- **What:** Every public transport stop in the UK — bus, rail, tram, ferry
- **Publisher:** Department for Transport
- **Format:** CSV download from data.gov.uk
- **Key fields:** ATCO code (unique stop ID), name, latitude, longitude, stop type, status
- **Filtering needed:** Keep only active bus stops (stop type = 'BCT' or 'BCS'), exclude rail/tram/ferry
- **Refresh:** Monthly snapshots
- **Volume:** ~400,000 bus stops in England (after filtering from ~700k+ total public transport nodes)

#### BODS (Bus Open Data Service)
- **What:** Route definitions, timetables, real-time vehicle locations
- **Publisher:** Department for Transport (mandatory for all English bus operators since 2021)
- **Format:** GTFS feeds and TransXChange XML per operator per region
- **Key fields:** Route ID, line name, stop sequence, departure times, operating days
- **Filtering needed:** Extract unique routes (not journey patterns — one route has many daily patterns). Handle cross-region routes that appear in multiple regional feeds.
- **Refresh:** Monthly (timetable changes); real-time (SIRI-VM, not needed for this platform)
- **Volume:** ~800-1,500 unique bus routes in England (exact count determined after cross-region deduplication)

#### Key Counting Challenge
A "route" in BODS is not always what a planner means by "route." BODS publishes journey patterns — a route running in both directions, with slight variations (school days vs non-school days), produces multiple pattern records per logical route. A route serving two regions appears in both regional feeds. The platform must define precisely:
- **BusStop:** One physical location, identified by ATCO code, counted once regardless of routes served
- **Route:** One named service, identified by route_id, counted once regardless of regions served or journey patterns

Getting these counts wrong (e.g., counting stop-route assignments instead of unique stops, or counting cross-region duplicates as separate routes) would inflate per-capita metrics by 3-10x and destroy all downstream analysis.

### 5.2 Demographic & Socio-Economic Data

#### ONS Census 2021
- **What:** Population, age distribution, ethnicity, household composition, car ownership at neighbourhood (LSOA) level
- **Publisher:** Office for National Statistics
- **Format:** CSV via NOMIS API or bulk download
- **Geography:** 33,755 LSOAs (Lower Layer Super Output Areas) in England, each ~1,500 residents
- **Key fields per LSOA:** Total population, % aged 0-15/16-64/65+, % no car, ethnic composition
- **Refresh:** Decennial (next: 2031). This is static for the lifetime of the platform.

#### IMD 2019 (Index of Multiple Deprivation)
- **What:** England's official measure of relative deprivation at LSOA level
- **Publisher:** Ministry of Housing, Communities & Local Government
- **Format:** CSV download
- **Key fields:** LSOA code, IMD score (continuous), IMD decile (1=most deprived, 10=least)
- **Refresh:** Irregular (last: 2019, next: TBD). Static for now.

#### NOMIS Labour Market Data
- **What:** Unemployment rates, economic activity, business counts at MSOA level
- **Publisher:** Office for National Statistics via NOMIS
- **Format:** API (JSON/CSV)
- **Geography:** MSOAs (Middle Layer Super Output Areas, ~7,000 in England, each ~7,500 residents). Must be distributed to LSOAs for join with stop data.
- **Refresh:** Quarterly

#### ONS Geographic Boundaries
- **What:** GeoJSON polygons for regions, LSOAs, MSOAs
- **Publisher:** ONS Geography
- **Format:** GeoJSON
- **Used for:** Point-in-polygon stop-to-LSOA assignment, choropleth maps

### 5.3 Regional Structure

England has 9 statistical regions (ONS classification):

| ONS Code | Region Name | Population (2021) |
|----------|-------------|-------------------|
| E12000001 | North East England | ~2.6M |
| E12000002 | North West England | ~7.4M |
| E12000003 | Yorkshire and the Humber | ~5.5M |
| E12000004 | East Midlands | ~4.9M |
| E12000005 | West Midlands | ~5.9M |
| E12000006 | East of England | ~6.3M |
| E12000007 | Greater London | ~8.8M |
| E12000008 | South East England | ~9.2M |
| E12000009 | South West England | ~5.7M |
| | **Total** | **~56.3M** |

The 9 regions are exhaustive — they cover 100% of England's population. The sum of regional populations (~56.3M) equals the ONS Census 2021 total for England. There is no "10th region" or uncovered area. The platform's primary analytical unit is the region. Drill-down to LSOA level for demographic correlations and equity analysis.

### 5.4 Compliance Standards

#### TAG 2024 (Transport Appraisal Guidance)
Published by DfT, mandatory for all transport business cases submitted to HM Treasury.

| Parameter | Value | Source |
|-----------|-------|--------|
| Value of bus commuting time | £9.85/hour | TAG Data Book A1.3.1 (2022 prices) |
| Value of car commuting time | £12.65/hour | TAG Data Book A1.3.1 |
| Value of business travel time | £28.30/hour | TAG Data Book A1.3.1 |
| Value of leisure travel time | £7.85/hour | TAG Data Book A1.3.1 |
| Carbon value (central) | £80/tonne CO2e | BEIS/DESNZ 2024 |
| Social discount rate | 3.5% per annum | HM Treasury Green Book Ch.6 |
| Bus CO2 emissions | 0.0965 kg/passenger-km | DEFRA 2024 |
| Car CO2 emissions | 0.171 kg/km | DEFRA 2024 |

#### BCR (Benefit-Cost Ratio) Bands
| BCR | Value for Money Category |
|-----|--------------------------|
| < 1.0 | Poor |
| 1.0 – 1.5 | Low |
| 1.5 – 2.0 | Medium |
| 2.0 – 4.0 | High |
| > 4.0 | Very High |

#### Investment Unit Costs (2024 Prices)
| Item | Urban | Rural |
|------|-------|-------|
| Bus stop installation (standard) | £15,000 | £15,000 |
| Bus stop installation (DDA accessible) | £35,000 | £35,000 |
| Route annual operating cost | £250,000 | £180,000 |
| Single-deck bus purchase | £200,000 | £200,000 |
| Double-deck bus purchase | £300,000 | £300,000 |

---

## 6. System Architecture: Design Decisions From First Principles

### 6.1 The Fundamental Choice: Pre-Compute vs Runtime Compute

The platform must support rapid filter changes (user selects a region, toggles urban/rural) and show results in under 1 second. There are two approaches:

**Option A: Compute at runtime**
```
User changes filter → Load raw data → Filter → Aggregate → Compute metrics → Generate narrative → Render chart
Latency: 3-8 seconds depending on data volume
```

**Option B: Pre-compute offline, look up at runtime**
```
Build time: Compute all metrics for every possible filter combination → Store as indexed key-value pairs
User changes filter → Look up pre-computed result → Render chart from pre-built data
Latency: <100ms
```

**Decision: Option B.** The filter space is finite and small:
- 10 region choices (All + 9 specific regions) × 3 area types (All + Urban + Rural) = **30 combinations**
- 30 combinations × ~43 analytical sections = **~1,290 pre-computed results**
- At ~10KB per result (metrics + chart data + narrative) = **~13MB total**

This is trivially small. Pre-computing it all takes maybe 10 minutes at build time but makes runtime instantaneous. There is no reason to recompute the same metrics thousands of times when the underlying data changes only monthly.

This decision shapes the entire architecture: the data layer produces a **warehouse** (a single file containing all pre-computed results), and the presentation layer is a **thin rendering shell** that reads from it.

### 6.2 Architecture Layers

```
┌─────────────────────────────────────────────────┐
│              PRESENTATION LAYER                  │
│  Streamlit: filters → DuckDB lookup → Plotly     │
│  Thin shell. No computation. No data loading.    │
└─────────────────┬───────────────────────────────┘
                  │ reads from
┌─────────────────▼───────────────────────────────┐
│              WAREHOUSE (aequitas.duckdb)          │
│  Pre-computed: stats, charts, narratives         │
│  For every filter combination × every section    │
│  Built offline. Deployed as single file.         │
└─────────────────┬───────────────────────────────┘
                  │ built by
┌─────────────────▼───────────────────────────────┐
│              INTELLIGENCE LAYER                   │
│  InsightEngine: metrics → rules → templates      │
│  Evidence-gated. TAG 2024 compliant.             │
│  Runs at BUILD TIME, not runtime.                │
└─────────────────┬───────────────────────────────┘
                  │ operates on
┌─────────────────▼───────────────────────────────┐
│              DATA LAYER                           │
│  Ingest → Parse → Deduplicate → Enrich → Validate│
│  Pydantic schemas at every boundary.             │
│  Parquet intermediate format. Monthly refresh.   │
└─────────────────────────────────────────────────┘
```

### 6.3 Why This Layering

| Principle | Rationale |
|-----------|-----------|
| **Data layer has no knowledge of presentation** | If we swap Streamlit for a REST API tomorrow, zero data code changes |
| **Intelligence layer has no knowledge of Streamlit** | Engine runs identically in a CLI, in a test, or in a notebook |
| **Presentation layer has no business logic** | Pages are 50-100 lines of fetch → render, not 1,500 lines of computation |
| **Warehouse is the single artefact** | One file to deploy. One file to validate. One file to version. |
| **Pre-computation eliminates runtime complexity** | No caching bugs. No race conditions. No slow filter changes. |

### 6.4 Package Structure

```
src/aequitas/
├── core/                    # Domain models, constants, validators
│   ├── models.py            # Pydantic: BusStop, Route, LSOA, Region
│   ├── constants.py         # TAG 2024 values, BCR bands, region codes
│   └── validators.py        # ATCO code, LSOA code, coordinate range checks
│
├── ingestion/               # Download from government APIs → data/raw/
│   ├── naptan.py            # NaPTAN stops
│   ├── bods.py              # BODS routes (GTFS + TransXChange)
│   ├── census.py            # ONS Census via NOMIS
│   ├── imd.py               # IMD 2019
│   └── boundaries.py        # GeoJSON region/LSOA boundaries
│
├── processing/              # Transform raw/ → processed/ (Parquet)
│   ├── parser.py            # GTFS/TransXChange format detection + parsing
│   ├── geocoder.py          # Stop → coordinate enrichment from NaPTAN
│   ├── lsoa_linker.py       # Stop → LSOA spatial assignment (point-in-polygon)
│   ├── deduplicator.py      # Cross-region stop/route deduplication
│   ├── demographic_merger.py # LSOA demographics → stop-level enrichment
│   └── aggregator.py        # Neighbourhood → region → national summaries
│
├── intelligence/            # Narrative generation
│   ├── engine.py            # Orchestrator: context → metrics → rules → templates
│   ├── context.py           # Filter state → analytical scope detection
│   ├── calc.py              # Statistical calculators (Pearson r, Gini, BCR, gap analysis)
│   ├── rules.py             # Evidence-gated insight rules (fire only when data sufficient)
│   ├── templates.py         # Jinja2 consulting-tone narrative templates
│   └── config.py            # Per-section MetricConfig definitions
│
├── warehouse/               # Build aequitas.duckdb from processed data
│   ├── schema.py            # DuckDB table definitions
│   ├── builder.py           # Orchestrate: load → compute all sections → store
│   ├── precompute.py        # For each filter combo × section: run engine, store result
│   └── manifest.py          # Build metadata, checksums, ground truth values
│
├── rag/                     # Chatbot: retrieval-augmented generation
│   ├── indexer.py           # Build FAISS index from pre-computed narratives
│   ├── retriever.py         # Similarity search at query time
│   ├── grounding.py         # Citation enforcement, prohibited pattern detection
│   └── chatbot.py           # LLM integration (Gemini primary, Qwen fallback)
│
├── ml/                      # Machine learning models
│   ├── clustering.py        # Route archetype clustering (sentence-transformers + HDBSCAN)
│   ├── anomaly.py           # Service gap detection (Isolation Forest)
│   └── prediction.py        # Coverage prediction (Random Forest)
│
├── presentation/            # Streamlit (thin rendering layer)
│   ├── app.py               # Entry point
│   ├── sidebar.py           # Global region + urban/rural filter
│   ├── components/          # Reusable UI: chart builders, narrative displays, map
│   └── pages/               # One page per category (fetch + render, no logic)
│
├── validation/              # Ground truth checks, integrity verification
│   ├── ground_truth.py      # Known-correct values, sanity bounds
│   ├── consistency.py       # Cross-source checks (warehouse matches processed matches raw)
│   └── health_check.py      # Runtime startup check for deployed dashboard
│
└── pipeline/
    └── cli.py               # python -m aequitas.pipeline.cli --stage=all

tests/                       # pytest suite
├── test_entity_counts.py    # Deduplication correctness
├── test_national_averages.py # Population-weighted, not simple mean
├── test_engine_rules.py     # Evidence-gating: suppress when data insufficient
├── test_filter_matrix.py    # All 30 combinations return valid results
├── test_narratives.py       # No rendering errors, no NaN, no hardcoded text
├── test_provenance.py       # Every metric traceable to source
└── test_warehouse.py        # Schema integrity, row counts
```

---

## 7. Phase Zero: Know the Data Before Writing a Line of Code

Before touching architecture, before writing a Pydantic model, before choosing between DuckDB and Parquet — sit down with the raw data and understand exactly what you have.

This is not optional. This is not "exploration." This is the foundation. Every architectural decision, every entity definition, every sanity bound in a validator comes from knowing what the data actually contains, how it's structured, where it's broken, and what it can and cannot tell you. Skipping this step is how you end up with a platform that counts 779,262 "stops" when there are actually 68,572 physical locations — and then builds 43 analytical sections on top of that wrong number.

### 7.1 What "Know the Data" Actually Means

It means answering these questions with evidence, not assumptions, before any code is written:

**For every data source (NaPTAN, BODS, Census, IMD, etc.):**

1. **What is one row?** Not what the documentation says a row is — what does a row actually represent when you open the file and look at it? In NaPTAN, is one row a physical bus stop, or a platform within a station, or a stop-route assignment? The answer changes everything downstream.

2. **What is the unique identifier?** Which column(s) uniquely identify a record? Is `stop_id` truly unique, or do you see the same `stop_id` appear multiple times with different attributes? If the same stop appears 11 times (once per route it serves), your "stop count" is 11x your actual stop count.

3. **What are the actual column names, types, and value ranges?** Not what the API documentation says — what the CSV header row actually contains. Column names drift across data source versions. A column called `UrbanRural` in one file might be called `urban_rural_classification` in another. A population column might be an integer in one source and a string with commas in another.

4. **What is the geographic scope?** NaPTAN covers all of the UK — bus, rail, tram, ferry, across England, Scotland, Wales, Northern Ireland. BODS covers only England. Census 2021 covers England and Wales. If you join NaPTAN with BODS without filtering, you get Scottish bus stops with no route data, which silently inflates stop counts while adding zero analytical value.

5. **What are the join keys between sources?** Stops join to LSOAs via spatial coordinates (point-in-polygon). LSOAs join to demographics via `lsoa_code`. Routes join to stops via stop sequences in TransXChange/GTFS. What is the match rate? If you join stops to LSOA demographics and only 60% match, your per-capita metrics are computed on a biased subset. You need to know this before you design the pipeline, not after.

6. **What is the population denominator?** This is the single most consequential number in the platform. Every per-capita metric (stops per 1,000, routes per 100,000) divides by population. Is that the total ONS Census 2021 population for all of England (~56.3M)? Or only the population of LSOAs that have bus stops? Or only the population of LSOAs that successfully joined to your processed data? These three numbers can differ by 40%. Using the wrong one makes every chart, every ranking, every narrative, every investment calculation wrong — and wrong in a way that a DfT statistician will catch.

7. **What does "duplicate" mean in this context?** A bus stop appearing in both the Yorkshire BODS feed and the North West BODS feed is one stop, not two. A route serving both regions is one route, not two. A journey pattern (outbound Monday, inbound Monday, outbound Saturday) is not three routes — it's one route with three patterns. If you don't define deduplication rules before building the pipeline, you will count duplicates as distinct entities and never notice, because the per-capita metrics will still look plausible at a glance.

8. **What is missing?** Which LSOAs have zero bus stops? (That's a valid analytical finding — a "coverage desert" — but only if it's real and not a data gap.) Which regions have suspiciously low or high route counts? Which demographic fields have null values, and what is the null rate?

### 7.2 How to Do This Concretely

**Step 1: Profile every raw file.**

Open a notebook. For each CSV/GeoJSON/XML:
```
- File name, source, download date
- Row count
- Column names (exact, verbatim)
- Column types (string, int, float, date)
- Unique value counts for key columns (stop_id, route_id, lsoa_code)
- Null rates per column
- Min/max/mean for numeric columns
- Sample of 5 rows (to see what the data actually looks like)
```

This takes 2-3 hours for all sources. It prevents 2-3 weeks of debugging later.

**Step 2: Establish the counting facts.**

Before any pipeline code exists, answer these with SQL or Pandas in a scratch notebook:

```
NaPTAN:
  Total rows in Stops.csv: ___
  Rows where StopType is bus (BCT/BCS/BCE): ___
  Unique stop_ids after bus-type filter: ___
  Stops with valid lat/lon within England bounds: ___

BODS (across all 9 regional feeds):
  Total route records across all regions: ___
  Unique route_ids across all regions: ___
  Routes appearing in multiple regions (cross-region duplication count): ___
  Unique route_ids after cross-region deduplication: ___

Census:
  Total LSOAs in population file: ___
  Total population sum across all LSOAs: ___
  Total population sum across 9 English regions: ___

Joins:
  Stops successfully assigned to an LSOA (match rate): ___
  LSOAs with at least one bus stop: ___
  LSOAs with zero bus stops: ___
  Population in LSOAs with bus coverage: ___
  Population in LSOAs without bus coverage: ___
```

Write these numbers down. They become the ground truth. Every number the platform ever displays must trace back to these.

**Step 3: Identify the traps.**

Every government dataset has quirks that aren't in the documentation. Find them before they find you:

- NaPTAN includes rail stations, ferry terminals, tram stops, and taxi ranks alongside bus stops. If you don't filter by stop type, your "bus stop count" includes 300,000 non-bus entities.
- BODS TransXChange XML uses `JourneyPattern` elements that represent individual trips, not routes. One route with 40 daily trips produces 40+ pattern elements. Counting patterns as routes inflates route counts by 10-100x.
- Cross-region routes appear in multiple BODS regional feeds. First Bus route 2089 might appear in the Yorkshire feed AND the East Midlands feed. If you sum route counts per region, you double-count cross-region routes.
- ONS Census population is available at different geographic levels (LSOA, MSOA, Local Authority, Region). The sum of LSOA populations for a region should match the official regional population. If it doesn't, you're using a filtered or partial population file.
- IMD 2019 covers 32,844 LSOAs (it was published before the 2021 LSOA boundary changes). Census 2021 has 33,755 LSOAs. The ~900 difference means some 2021 LSOAs have no IMD score. Decide how to handle this before building the merge pipeline.
- Unemployment data from NOMIS is published at MSOA level (~7,000 areas), not LSOA level (~33,000 areas). Distributing MSOA values to constituent LSOAs requires a lookup table and a distribution assumption (usually: all LSOAs in an MSOA share the same rate).

**Step 4: Decide the population denominator.**

This deserves its own step because it affects every per-capita metric.

Option A: Total ONS regional population (~56.3M for England). This is the academically correct denominator for "routes per 100,000 population" — it answers "how many routes exist per capita in this region."

Option B: Population of LSOAs with bus coverage only. This answers a different question: "among people who have some bus access, how dense is the service?"

Option C: Population of LSOAs that successfully joined in your pipeline. This is what happens by accident when join failures silently drop LSOAs. It answers no coherent question and produces metrics that don't match any published population figure.

**The choice must be explicit, documented, and consistent across the entire platform.** The blueprint recommends Option A (total ONS regional population) for all per-capita metrics, with Option B available as a secondary metric for coverage-specific analysis.

**Step 5: Write a data dictionary.**

Before any pipeline code: a single document listing every column in every source file with its meaning, type, join key relationships, known quirks, and null handling strategy. This is the contract between the person who understands the data and the code that processes it. Without it, the code is guessing.

### 7.3 Why This Comes Before Architecture

The temptation is to start with the interesting parts — the InsightEngine, the dashboard, the chatbot. But every interesting part operates on data. If the data is wrong, the interesting parts are wrong.

A narrative engine that generates "North East has 23.21 stops per 1,000 population" is not impressive if the actual number is 1.83 and the difference is because nobody checked whether `len(df)` counts unique stops or stop-route records.

Spending a week understanding the data before writing code is not wasted time. It is the single highest-leverage activity in the entire project. Every fact established in this phase — every row count verified, every join key tested, every population denominator confirmed — prevents a class of bugs that would otherwise survive undetected through the entire pipeline and appear on the dashboard as a confidently-stated wrong number.

---

## 8. Data Layer: Ingestion, Processing, Warehouse

### 8.1 Entity Definitions (The Contract)

These come directly from the data audit in Section 7. Every definition below is a fact established by profiling the raw files, not an assumption from API documentation.

**BusStop:** A single physical location where a bus can stop. Identified by ATCO code. Counted **once** regardless of how many routes serve it. Belongs to exactly one LSOA (determined by coordinates). Belongs to exactly one region (determined by LSOA).

**Route:** A named bus service operating between defined endpoints. Identified by route_id. Counted **once** regardless of how many regions it serves or how many daily journey patterns it runs. A route serving Yorkshire and North West is one route that records `regions_served = [yorkshire, north_west]`.

**LSOA:** An ONS geographic unit of ~1,500 residents. 33,755 exist in England. An LSOA "has bus coverage" if at least one BusStop falls within its boundary polygon.

**Region:** One of 9 ONS statistical regions of England. Population from Census 2021.

These definitions are enforced as Pydantic models with validators. Any pipeline stage that produces output violating these models fails loudly at the stage boundary — not silently two weeks later on the dashboard.

```python
class BusStop(BaseModel):
    stop_id: str           # NaPTAN ATCO code (8-12 chars)
    stop_name: str
    latitude: float        # Must be within 49.8-60.9 (UK bounds)
    longitude: float       # Must be within -8.2 to 1.8 (UK bounds)
    lsoa_code: str         # Must match E01XXXXXX pattern
    region_code: RegionCode
    urban_rural: Literal["urban", "rural"]

class Route(BaseModel):
    route_id: str
    line_name: str
    route_length_km: float
    num_stops: int
    trips_per_day: int
    regions_served: list[RegionCode]  # One route may serve multiple regions

class RegionSummary(BaseModel):
    region_code: RegionCode
    population: int
    unique_stops: int              # stop_id nunique, NOT len(df)
    unique_routes: int             # Cross-region deduplicated
    stops_per_1000: float          # unique_stops / population * 1000
    routes_per_100k: float         # unique_routes / population * 100_000

    @field_validator('stops_per_1000')
    def sanity_check(cls, v):
        if v > 30:
            raise ValueError(
                f'stops_per_1000={v} exceeds sanity bound. '
                'Are you counting stop-route records instead of unique stops?'
            )
        return v
```

The `sanity_check` validator is the single most important piece of code in the platform. It catches the class of error where stop-route records (many per stop) get counted as unique stops. With ~400k unique bus stops across ~56M population, the true national stops_per_1000 should be ~7. A region-level value exceeding 30 (the validator threshold) would indicate a systematic counting error — for example, counting each stop once per route it serves rather than once per physical location. This is **design-level error prevention**, not testing-level.

### 8.2 Ingestion

**Goal:** Download raw data from government APIs into timestamped local files.

```
python -m aequitas.pipeline.cli --stage=ingest

Output:
data/raw/
├── naptan/stops_2024-10-15.csv
├── bods/east_england/routes_2024-10-15.zip
├── bods/north_west/routes_2024-10-15.zip
├── ... (9 regions)
├── census/population_by_lsoa_2021.csv
├── imd/imd_2019_scores.csv
├── demographics/car_ownership_2021.csv
├── demographics/unemployment_2024.csv
├── demographics/age_distribution_2021.csv
├── demographics/ethnicity_2021.csv
└── boundaries/regions.geojson
```

**Key decisions:**
- **Date-stamped files.** Never overwrite previous downloads. Enables diff-based debugging ("what changed between October and November?").
- **YAML-configured.** Region names, API endpoints, column mappings in `config/ingestion.yaml`. Zero hardcoded URLs.
- **SHA256 checksum** on every file, logged to `manifest.json`.
- **Idempotent.** Re-running with the same date produces identical output.

### 8.3 Processing

**Goal:** Transform raw downloads into clean, validated, deduplicated Parquet files.

Six sequential steps, each with input schema → processing → output schema validation:

#### Step 1: Parse
- Detect format (GTFS vs TransXChange) per regional BODS feed
- Extract stop references, route definitions, timetable data
- Normalize to common schema regardless of source format
- **Output:** `parsed_stops.parquet`, `parsed_routes.parquet`

#### Step 2: Geocode + LSOA Assignment
- Match every stop to NaPTAN coordinates (by ATCO code)
- Point-in-polygon: stop coordinates → LSOA boundary → `lsoa_code`
- Determine region from LSOA's containing region polygon
- **Validation:** >95% of stops successfully assigned to an LSOA
- **Fallback:** Stops near LSOA boundaries assigned to nearest LSOA centroid
- **Output:** `stops_with_geography.parquet`

#### Step 3: Cross-Region Deduplication

This is where the critical counting logic lives:

```python
def deduplicate_stops(regional_stop_dfs: list[DataFrame]) -> DataFrame:
    """A stop appearing in multiple regional feeds is ONE stop."""
    combined = pd.concat(regional_stop_dfs)
    unique = combined.drop_duplicates(subset='stop_id', keep='first')
    assert unique['stop_id'].nunique() == len(unique)
    return unique

def deduplicate_routes(regional_route_dfs: list[DataFrame]) -> DataFrame:
    """A route serving two regions is ONE route with regions_served=[r1, r2]."""
    combined = pd.concat(regional_route_dfs)
    routes = combined.groupby('route_id').agg({
        'line_name': 'first',
        'route_length_km': 'first',
        'num_stops': 'first',
        'trips_per_day': 'max',          # Take the highest frequency
        'region_code': lambda x: list(set(x)),  # Collect all regions
    }).rename(columns={'region_code': 'regions_served'}).reset_index()
    return routes
```

- **Output:** `unique_stops.parquet`, `unique_routes.parquet`
- **Validation:** Total unique stops < 500,000 (sanity); total unique routes < 5,000 (sanity)

#### Step 4: Demographic Enrichment
- For each LSOA, join demographic data:
  - Population + age distribution (Census 2021)
  - IMD score + decile (IMD 2019)
  - Unemployment rate (NOMIS 2024)
  - Car ownership % (Census 2021)
  - Ethnic composition (Census 2021)
- LSOA code is the universal join key across all datasets
- **Validation:** >97% merge rate per demographic field
- **Memory management:** Process region-by-region with `gc.collect()` between merges for large datasets
- **Output:** `lsoa_demographics.parquet`, `stops_enriched.parquet`

#### Step 5: Aggregation

```python
def compute_national_average(regional_summaries: list[RegionSummary]) -> dict:
    """Population-weighted national averages.

    Simple mean across regions is WRONG — it treats a region of 2M
    equally with a region of 9M. The correct national average is:
    total_entity_count / total_population * scale_factor
    """
    total_pop = sum(r.population for r in regional_summaries)
    total_stops = sum(r.unique_stops for r in regional_summaries)
    total_routes = sum(r.unique_routes for r in regional_summaries)
    return {
        'stops_per_1000': total_stops / total_pop * 1000,
        'routes_per_100k': total_routes / total_pop * 100_000,
    }
```

- Compute per-region summaries (unique counts, per-capita metrics, ranks)
- Compute national averages (population-weighted, never simple mean)
- Compute LSOA-level metrics for correlation and equity analysis
- **Output:** `regional_summaries.parquet`, `national_stats.json`, `lsoa_metrics.parquet`

#### Step 6: Validation Gate

```bash
python -m aequitas.pipeline.cli --stage=validate
```

Checks:
- Entity count sanity (stops < 500k, routes < 5k, per-capita metrics within bounds)
- Cross-source consistency (sum of regional stops ≤ national total)
- Population total matches ONS official figure (±100 for rounding)
- Region count = 9
- Every per-capita metric is population-weighted
- Every LSOA code matches E01XXXXXX pattern
- Demographic merge rates > 95%

**If any check fails: pipeline halts.** No silent corruption. No "fix later."

### 8.4 Warehouse Build

**Goal:** A single DuckDB file containing everything the dashboard needs.

```bash
python -m aequitas.pipeline.cli --stage=warehouse
```

DuckDB schema:
```sql
-- Source tables (for chatbot context and drilldown)
CREATE TABLE stops (stop_id VARCHAR PRIMARY KEY, ...);
CREATE TABLE routes (route_id VARCHAR PRIMARY KEY, ...);
CREATE TABLE lsoa_demographics (lsoa_code VARCHAR PRIMARY KEY, ...);

-- The key table: pre-computed results for every filter × section
CREATE TABLE section_results (
    region      VARCHAR,     -- 'all' or region_code
    urban_rural VARCHAR,     -- 'all', 'urban', 'rural'
    section_id  VARCHAR,     -- 'A1', 'B3', 'D5', etc.
    stats       JSON,        -- Computed metrics
    chart_data  JSON,        -- Plotly-serializable chart specification
    narrative   JSON,        -- Pre-rendered InsightEngine output
    PRIMARY KEY (region, urban_rural, section_id)
);
-- 30 filter combos × 43 sections = 1,290 rows. ~13MB total.

-- Provenance: trace any metric to its source
CREATE TABLE provenance (
    metric_id    VARCHAR PRIMARY KEY,   -- 'north_east.routes_per_100k'
    value        DOUBLE,                -- 5.94
    formula      VARCHAR,               -- 'unique_routes / population * 100000'
    inputs       JSON,                  -- {"unique_routes": 156, "population": 2626400}
    source_files VARCHAR[]
);
```

**Build process:** For each of the 1,290 (filter × section) combinations:
1. Load filtered data from processed Parquet
2. Run InsightEngine → get stats, narrative
3. Build Plotly chart data
4. Insert into DuckDB

This takes ~10-15 minutes. It runs once per data refresh (monthly), not on every page load.

---

## 9. Intelligence Layer: How Numbers Become Narratives

### 9.1 The Problem With Hardcoded Text

A dashboard page that shows a chart and then says:

> *"East of England has good bus coverage with extensive routes."*

...is useless to a policy maker. It's vague, unquantified, and doesn't change when the user switches to a different region or filter.

What a policy maker needs:

> *"East of England has 2.54 bus stops per 1,000 population, ranking #1 of 9 English regions. This is 28.7% above the national average of 1.97 stops per 1,000. Despite leading nationally, this represents approximately 1 stop per 394 residents."*

This narrative must:
- Change dynamically when the user selects a different region
- Show different content for "All Regions" (comparative ranking) vs "Single Region" (vs national average) vs "Urban Only" (descriptive, no ranking)
- Suppress itself when data is insufficient (e.g., don't show a correlation insight when p > 0.05)
- Always use population-weighted averages, never simple means
- Cite TAG 2024 values when making investment recommendations

### 9.2 InsightEngine Architecture

Five layers, each with a single responsibility:

#### Layer 1: Context Resolver
Detects what kind of analysis is appropriate for the current filter state.

```
Filter: "All Regions" + "All" → scope: all_regions (9 groups, show rankings)
Filter: "Yorkshire" + "All"  → scope: single_region (1 group, compare to national avg)
Filter: "All Regions" + "Urban" → scope: subset (1 aggregated group, descriptive only)
```

**Why this matters:** Showing "Yorkshire ranks #3 of 9" makes sense for single_region scope. Showing "Urban areas rank #1 of 1" for subset scope is meaningless. The context resolver prevents nonsensical insights.

#### Layer 2: Calculators
Pure functions that compute statistical metrics. No presentation logic.

| Calculator | Input | Output |
|-----------|-------|--------|
| `rank_regions()` | DataFrame with per-region metrics | Ranks 1-9, best/worst, % vs national avg |
| `describe_distribution()` | Series of values | Mean, median, std, CV, IQR, outliers |
| `calculate_correlation()` | Two series | Pearson r, p-value, strength label, significance |
| `calculate_gini()` | Coverage values + population weights | Gini coefficient (0=equality, 1=inequality) |
| `calculate_bcr()` | Investment cost, projected benefits | BCR, VfM category (Poor/Low/Medium/High/Very High) |
| `calculate_gap_to_target()` | Current values, target value | Gap absolute, gap %, regions below target |
| `calculate_investment_needed()` | Gap, unit costs, discount rate | NPV, annual cost, undiscounted total |

All calculators use TAG 2024 constants from a single source-of-truth constants file.

#### Layer 3: Evidence-Gated Rules
Rules that fire only when their data requirements are met. This is the credibility guarantee.

| Rule | Fires When | Produces | Suppresses When |
|------|-----------|----------|-----------------|
| RankingRule | n_groups ≥ 3, extrema exist | Best/worst ranking with national avg | Fewer than 3 groups (e.g., urban subset) |
| SingleRegionRule | scope == single_region | Region rank vs all 9, % above/below national | Not single-region scope |
| SubsetSummaryRule | scope == subset, n_groups == 1 | Descriptive stats, no ranking | n_groups > 1 |
| CorrelationRule | n ≥ 30, p < 0.05 | r value, strength, direction | Insufficient sample or not significant |
| GapToInvestmentRule | Regions below target exist | Investment needed (£), BCR | All regions above target |
| VariationRule | CV > 10% | Variation coefficient, label | Low variation (not noteworthy) |
| OutlierRule | Outliers detected (>1.5× IQR) | Named outlier regions | No outliers |
| GiniEquityRule | n ≥ 100 LSOA observations | Gini, equity interpretation | Too few observations |
| PowerLawRule | Valid log-log correlation | Scaling relationship | No valid fit |
| EfficiencyRule | Underserved areas identified | % underserved, additional stops needed | No underserved areas |

**The key principle: it is always better to show nothing than to show a misleading insight.** A policy maker who sees "insufficient data for correlation analysis" trusts the platform. A policy maker who sees "strong correlation (p=0.38)" does not — and never will again.

#### Layer 4: Templates
Jinja2 templates that produce consulting-tone text from rule outputs.

```jinja2
{# Ranking template — fires for all_regions scope #}
**{{ best.name }}** leads England with **{{ best.value|round(2) }} {{ unit }}**,
{{ best.pct_above|round(1) }}% above the national average of
{{ national_avg|round(2) }} {{ unit }}.

**{{ worst.name }}** has the lowest at **{{ worst.value|round(2) }} {{ unit }}**
({{ worst.pct_below|round(1) }}% below average), serving a population of
{{ (worst.population / 1e6)|round(1) }} million.

The {{ variation_factor|round(1) }}× gap between best and worst regions
{{ "indicates significant regional inequality in bus provision"
   if variation_factor > 3
   else "suggests moderate variation across regions" }}.
```

#### Layer 5: Orchestrator
Coordinates all four layers:

```python
class InsightEngine:
    def run(self, df, config, filters) -> dict:
        context = resolve_context(df, config.groupby, filters)
        metrics = self.compute_metrics(df, config, context)
        insights = self.apply_rules(context, metrics, config.rules)
        rendered = self.render(insights)
        return {
            'summary': rendered.summary,
            'key_finding': rendered.key_finding,
            'recommendation': rendered.recommendation,
            'evidence': metrics,     # For provenance/audit
            'sources': config.sources,
        }
```

### 9.3 Why Not Just Hardcode?

With 43 sections × 30 filter combinations × 3 narrative components (summary, finding, recommendation) = **~3,870 unique narrative strings.** Writing these by hand is impossible. More importantly, when data refreshes monthly and metrics change, every hardcoded string must be manually updated — which means they won't be, and the dashboard will show stale text next to fresh charts.

The engine generates all 3,870 strings from ~20 templates × ~10 rules × real data. When data refreshes, all narratives regenerate automatically with correct values.

---

## 10. Presentation Layer: What Policy Makers Actually See

### 10.1 Design Philosophy

The dashboard is a **reading experience**, not an exploration tool. Policy makers don't want to "explore data" — they want to read answers to specific questions, supported by charts and quantified evidence, in a format they can copy into their business cases.

Each page answers the analytical questions from Section 4, in order, with:
1. A chart showing the pattern
2. A narrative explaining the pattern with exact numbers
3. A recommendation (where applicable) with BCR justification

### 10.2 Page Architecture

With pre-computation, every page becomes trivially simple:

```python
# pages/coverage.py — Category A: Coverage & Accessibility

import streamlit as st
from aequitas.presentation.sidebar import get_filters
from aequitas.presentation.data_access import get_section
from aequitas.presentation.components import render_chart, render_narrative

st.title("Coverage & Accessibility")
region, urban_rural = get_filters()

# Section A1
st.header("A1: Regional Route Density")
data = get_section('A1', region, urban_rural)  # DuckDB lookup, <10ms
render_chart(data['chart_data'])
render_narrative(data['narrative'])

st.divider()

# Section A2
st.header("A2: Regional Stop Density")
data = get_section('A2', region, urban_rural)
render_chart(data['chart_data'])
render_narrative(data['narrative'])

# ... A3 through A8 follow the same pattern
```

**Each page: ~100-200 lines.** No Pandas. No CSV loading. No InsightEngine calls. No caching decorators. Just fetch and render.

### 10.3 Global Sidebar

A single filter panel that persists across all pages:

```
┌─────────────────────────┐
│  Geographic Scope       │
│  [All Regions      ▼]  │
│                         │
│  Area Type              │
│  ○ All                  │
│  ○ Urban Only           │
│  ○ Rural Only           │
│                         │
│  ─────────────────────  │
│  Data Currency          │
│  Stops: NaPTAN Oct 2024 │
│  Routes: BODS Oct 2024  │
│  Census: ONS 2021       │
│  IMD: 2019              │
│  Built: 2026-03-10      │
└─────────────────────────┘
```

The sidebar also shows data provenance at all times — a subtle but important credibility signal for policy makers.

### 10.4 Homepage: Map-First

The landing page is a choropleth of England coloured by bus infrastructure density. Each region is clickable, navigating to that region's analysis. This matches how transport planners think — geographically, not categorically.

Below the map: headline statistics (total unique stops, total unique routes, total population covered, national average stops/1000) with the "last updated" date.

### 10.5 Visualization Standards

| Analysis Type | Chart Type | Why |
|---------------|-----------|-----|
| Regional comparison (9 regions) | Horizontal bar, sorted | Easy rank reading |
| Correlation (LSOA-level) | Scatter with regression line | Shows relationship + fit |
| Distribution | Box + violin overlay | Shows spread, outliers, and shape |
| Equity | Lorenz curve with Gini annotation | Standard equity visualization |
| Geographic pattern | Choropleth (Plotly Mapbox) | Spatial patterns visible at a glance |
| Time/frequency | Grouped bar or heatmap | Temporal patterns |
| Power law / scaling | Log-log scatter | Reveals scaling relationships |

**Colorblind-safe everywhere:** Viridis or Cividis colorscale. No red/green encoding.

**No chart without a narrative. No narrative without a chart.** They are paired: the chart shows the pattern, the narrative quantifies and interprets it.

---

## 11. Conversational Layer: RAG Chatbot for Policy Q&A

### 11.1 Why a Chatbot

Policy makers have ad-hoc questions that don't map neatly to the dashboard's section structure:

> "How does bus coverage in the North East compare to areas with similar deprivation levels?"

> "What would be the BCR of adding 50 new stops in rural South West?"

> "Which regions have the biggest gap between demographic need and service provision?"

A well-grounded chatbot answers these by synthesising across pre-computed narratives — something the section-by-section dashboard layout doesn't do naturally.

### 11.2 Architecture

```
User question → Embed (sentence-transformers, CPU, ~60ms)
             → FAISS search (~1,365 pre-computed narratives, <5ms)
             → Top-5 retrieval with confidence scores
             → Confidence gate:
                 Score < 0.3 → REFUSE ("I don't have sufficient data...")
                 Score 0.3-0.5 → ANSWER WITH CAVEAT ("Based on limited data...")
                 Score > 0.5 → ANSWER WITH CONFIDENCE
             → Grounding prompt (system instructions + retrieved context + question)
             → Gemini 1.5 Pro API (2-4 seconds)
             → Post-generation validation:
                 ✓ Contains [Source: ...] citation? → Pass
                 ✗ Contains prohibited pattern? → Block, regenerate
                 ✗ No citation? → Append disclaimer
             → Display response
```

### 11.3 What Gets Indexed

Every pre-computed narrative from the warehouse, plus supplementary context:

| Content Type | Count | Example |
|---|---|---|
| Section narratives (30 × 43) | ~1,290 | "North East has 1.23 routes/100k, ranking #7..." |
| Cross-region summaries | ~50 | "Coverage ranges from 0.89 to 2.54 stops/1000..." |
| Methodology notes | ~15 | "BCR uses TAG 2024 values: £9.85/hr bus commuting..." |
| Data source descriptions | ~10 | "NaPTAN: ~400k bus stops in England, monthly refresh" |
| **Total** | **~1,365** | Embedded with all-MiniLM-L6-v2 (384-dim) |

FAISS index: ~2MB. Exhaustive search (no approximation needed at this scale).

### 11.4 Guardrails (Non-Negotiable)

**System prompt:**
```
You are a transport policy analyst assistant. Answer ONLY using the provided
context documents. If the context does not contain the answer, say:
"I don't have sufficient data in my analytical reports to answer that."

NEVER: invent statistics, make causal claims, forecast, recommend policy
without data support, reference external sources.

ALWAYS: cite [Source: Category X, Section Y, Region Z], use exact numbers
from context, distinguish "national" from "regional".
```

**Post-generation prohibited patterns (regex scan):**
- Temporal: "will increase", "expected to", "by 2030"
- Causal: "caused by", "leads to", "results in" (without "correlated with")
- Unsupported: "should invest", "must improve" (unless quoting engine output)

### 11.5 Fallback Chain

```
Gemini 1.5 Pro (free: 1,500 req/day)
  ├── OK → respond
  └── Quota/error → Qwen 2.5 via HF Inference API (free)
        ├── OK → respond (with "slower model" indicator)
        └── Fail → "AI assistant temporarily unavailable"
```

### 11.6 Cost: Zero

| Component | Cost |
|-----------|------|
| Gemini 1.5 Pro free tier | £0 |
| FAISS (in-process, CPU) | £0 |
| Sentence-transformers (local) | £0 |
| Qwen fallback (HF Inference) | £0 |

---

## 12. Deployment & Operations

### 12.1 Hosting: Hugging Face Spaces (Free Tier)

| What | Size |
|------|------|
| `aequitas.duckdb` (warehouse) | ~50MB (Git LFS tracked) |
| FAISS index | ~2MB |
| ML models (.pkl × 3) | ~15MB |
| Streamlit app + package | ~2MB |
| **Total** | **~69MB** |

HF Spaces free tier: CPU-only, sufficient for a lookup-based dashboard. No GPU needed.

**Git LFS:** The DuckDB file is binary and must be tracked with LFS:
```bash
git lfs track "*.duckdb"
```

### 12.2 Monthly Data Refresh Pipeline

```
GitHub Actions cron (1st Monday, 02:00 UTC)
  │
  ├── Stage 1: Ingest (download from NaPTAN, BODS, NOMIS)
  ├── Stage 2: Process (parse, deduplicate, enrich, aggregate)
  ├── Stage 3: Validate (ground truth checks — MUST pass 100%)
  │     └── Fail → halt pipeline, create GitHub Issue
  ├── Stage 4: Warehouse build (DuckDB + InsightEngine pre-compute + FAISS index)
  ├── Stage 5: ML model retrain (on correct data from this month's refresh)
  │
  ├── Git commit + push → HF Spaces auto-deploys
  │
  └── Health check on deployed instance
        ├── Pass → live
        └── Fail → rollback to previous tag
```

**GitHub Actions budget:** Free tier = 2,000 min/month. Full pipeline ≈ 240 min. At 1 run/month = 12% of budget. Development runs should be local to preserve CI quota.

### 12.3 Monitoring

**Problem:** HF Spaces has no built-in alerting. A dashboard returning errors or stale data must be detected.

**Three layers:**

1. **Pipeline logs** (loguru, structured JSON): Every stage logs entry/exit with row counts and duration. On failure: halt + GitHub Issue with log excerpt.

2. **Startup health check:** Dashboard verifies warehouse integrity on every restart:
   - DuckDB file exists and schema matches
   - Manifest checksums valid
   - Ground truth spot checks pass
   - Data freshness < 90 days

3. **Uptime cron** (GitHub Actions, every 6 hours): HTTP check on HF Spaces URL. Non-200 → create GitHub Issue with `monitoring` label.

**Data staleness banners** (thresholds set to 1.5× the monthly refresh interval to catch missed refreshes):
| Warehouse Age | Dashboard Banner |
|--------------|-----------------|
| < 45 days | None (fresh — within expected refresh window) |
| 45-90 days | Yellow: "Transport data last updated [date]. A refresh may have failed." |
| > 90 days | Orange: "Data significantly outdated. Contact maintainer." |

If a monthly pipeline run fails (validation check, API error, etc.), the dashboard continues serving the previous month's data. The staleness banner at 45 days ensures this failure becomes visible to users within 2 weeks of the missed refresh, rather than silently serving stale data for months.

---

## 13. Quality System: How Trust Is Built and Maintained

### 13.1 The Trust Equation

For policy stakeholders:

```
Trust = Consistency × Traceability × Evidence-Gating

Consistency:  Same number everywhere it appears (chart = narrative = export)
Traceability: Every number traces to source data through a documented formula
Evidence-Gating: Insights suppress themselves when data is insufficient
```

One failure in any of these three → trust destroyed → platform abandoned.

### 13.2 Consistency Guarantees

**Single source of truth architecture.** Every metric is computed once, stored in DuckDB, and served to all consumers (charts, narratives, chatbot, PDF exports) from the same row. It is structurally impossible for a chart to show "2.54 stops/1000" while the narrative says "2.38 stops/1000" because both read from the same JSON blob.

**Population-weighted averages enforced at the calculator level.** The `compute_national_average()` function takes `unique_stops` and `population` as separate arguments and computes the ratio. It does not accept a pre-computed per-capita column (which would tempt someone to use `mean()` on it).

### 13.3 Traceability: Provenance Table

```sql
SELECT * FROM provenance WHERE metric_id = 'north_east.routes_per_100k';

-- Returns:
-- value: 5.94
-- formula: unique_routes / population * 100000
-- inputs: {"unique_routes": 156, "population": 2626400}
-- source_files: ["unique_routes.parquet", "lsoa_demographics.parquet"]
```

If a DfT official asks "where does this 5.94 come from?", the answer is one query away.

### 13.4 Evidence-Gating

| Situation | Wrong Response | Right Response |
|-----------|---------------|----------------|
| Correlation p = 0.38 | "Moderate correlation found" | [Section suppressed entirely] |
| Only 2 regions in filtered view | "Region A ranks #1 of 2" | Descriptive stats, no ranking |
| BCR cannot be computed (missing cost data) | "Investment recommended" | [Investment section suppressed] |
| Sample size n = 12 for correlation | "Weak negative correlation" | "Insufficient data (n < 30)" |

### 13.5 Testing Pyramid

```
                    ┌──────────┐
                    │ Manual QA│ ← 30 filter combos, visually verify
                    │ (deploy) │
                    ├──────────┤
                ┌───┤ Integra- │ ← Warehouse build → query → verify
                │   │ tion     │
                ├───┼──────────┤
            ┌───┤   │ Ground   │ ← Entity counts, sanity bounds, pop totals
            │   │   │ Truth    │
            ├───┼───┼──────────┤
        ┌───┤   │   │ Unit     │ ← Dedup logic, calculators, rule firing
        │   │   │   │ Tests    │
        └───┴───┴───┴──────────┘
```

**pytest suite runs in CI on every push.** Key tests:

| Test | What It Catches |
|------|----------------|
| `test_entity_counts` | Counting stop-route records instead of unique stops |
| `test_national_averages` | Using simple mean instead of population-weighted |
| `test_engine_rules` | Rules firing when they shouldn't (p > 0.05, n < 3) |
| `test_filter_matrix` | Empty or error results for any of 30 filter combos |
| `test_narratives` | "None", "NaN", "inf", or rendering errors in text |
| `test_provenance` | Metric on dashboard not traceable to source |

### 13.6 Ground Truth Values

Established after the first full pipeline run and locked:

| Metric | Expected Range | Validation |
|--------|---------------|-----------|
| Total unique bus stops | 350k-500k | After NaPTAN filter (bus only) + dedup |
| Total unique routes | 500-2,000 | After cross-region dedup |
| Total population (9 regions) | ~56.3M | ONS Census 2021 official |
| National stops/1000 | 6-9 | From unique stops (~400k) / total pop (~56M). Range bounded by stop count sanity bounds (350k-500k). |
| National routes/100k | 1-4 | From unique routes (~800-2k) / total pop (~56M) |
| Region count | 9 | Fixed |
| LSOA count (England) | 33,755 | Fixed |

Any value outside these ranges triggers a pipeline halt.

---

## 14. Build Sequence

### 14.1 Phase Dependencies

```
Phase 1: Data Foundation
  │ Gate: validate passes 100%, ground truth locked
  ▼
Phase 2: Warehouse + Intelligence
  │ Gate: DuckDB built, all 43 × 30 section results pre-computed
  ▼
Phase 3: Dashboard
  │ Gate: all pages render, all 30 filter combos verified
  ▼
Phase 4: Chatbot
  │ Gate: grounding > 95%, refusal > 80% for out-of-scope
  ▼
Phase 5: Deploy + Polish
  │ Gate: HF Spaces live, health check passing, PDF export working
  ▼
Operational
```

**No phase starts until the previous gate passes. No exceptions.**

### 14.2 Phase Details

#### Phase 1: Data Foundation (40% of effort)

Build: `core/models.py`, `ingestion/`, `processing/`, `validation/`, `pipeline/cli.py`

Deliverable: Clean, validated, deduplicated Parquet files with correct entity counts. `aequitas-validate` passes 100%.

**Why 40%:** This is where every counting error, every merge failure, every encoding issue lives. Getting this right first means everything downstream works. Getting it wrong means rebuilding everything later.

#### Phase 2: Warehouse + Intelligence (25% of effort)

Build: `intelligence/` (InsightEngine: engine, context, rules, calc, templates, config), `warehouse/` (schema, builder, precompute, manifest), `ml/` (train all 3 models on correct data)

Deliverable: `aequitas.duckdb` containing 1,290 pre-computed section results with stats, chart data, and narratives. All ML models trained on correct feature values.

#### Phase 3: Dashboard (15% of effort)

Build: `presentation/` (app, sidebar, components, pages)

Deliverable: 7 category pages + homepage + global sidebar. Each page: ~100 lines of fetch → render. All 30 filter combinations tested.

**Why only 15%:** With pre-computation done, pages are trivial. The heavy work was Phases 1-2.

#### Phase 4: Chatbot (10% of effort)

Build: `rag/` (indexer, retriever, grounding, chatbot)

Deliverable: FAISS index from ~1,365 narratives. Gemini integration with grounding enforcement. Chatbot panel on dashboard.

#### Phase 5: Deploy + Polish (10% of effort)

Build: HF Spaces deployment, Git LFS setup, GitHub Actions pipeline, PDF export (ReportLab), accessibility pass (colorscales, chart titles), monitoring (health check, uptime cron).

Deliverable: Live public dashboard on HF Spaces. Monthly automated refresh. PDF export per region.

### 14.3 Time Estimate (Solo Developer)

| Phase | Duration | Cumulative |
|-------|----------|-----------|
| Phase 1: Data Foundation | 2-3 weeks | Week 3 |
| Phase 2: Warehouse + Intelligence | 1.5-2 weeks | Week 5 |
| Phase 3: Dashboard | 1 week | Week 6 |
| Phase 4: Chatbot | 1 week | Week 7 |
| Phase 5: Deploy + Polish | 1 week | Week 8 |
| **Total** | **~7-8 weeks** | |

---

## 15. Technology Choices

Every choice is driven by the constraints: zero budget, solo developer, policy-maker audience, HF Spaces deployment.

| Decision | Choice | Why This | Why Not Alternative |
|----------|--------|----------|---------------------|
| **Warehouse** | DuckDB | Embedded (no server), columnar (fast analytics), single file (easy to deploy), works on HF Spaces | PostgreSQL needs server. SQLite is row-oriented. Parquet-only has no indexing. |
| **Intermediate format** | Parquet | Typed columns (no dtype guessing), compressed (3-5× smaller than CSV), DuckDB reads natively | CSV: untyped, slow, encoding issues. |
| **Presentation** | Streamlit | Free HF Spaces hosting. Single Python codebase. No frontend build toolchain. | Next.js: needs hosting + API backend. Two codebases for a solo developer. |
| **Charts** | Plotly | Interactive, professional, serializable to JSON (storable in DuckDB), Streamlit native integration | Matplotlib: static images, not interactive. Altair: fewer chart types. |
| **Narrative generation** | Custom InsightEngine (Jinja2 + rules) | Full control over evidence-gating. TAG 2024 compliance. Consulting tone. | LLM generation: not auditable, not reproducible, hallucination risk. |
| **Chatbot LLM** | Gemini 1.5 Pro | Free tier: 1,500 req/day. Quality 9/10 for analytical synthesis. | Claude/GPT-4: no free tier. LangChain: 15 transitive dependencies for no benefit. |
| **Chatbot fallback** | Qwen 2.5 (HF Inference) | Free tier. Quality 8-9/10. | No other free option with acceptable quality. |
| **Vector store** | FAISS (faiss-cpu) | ~1,365 docs fit in RAM trivially. <5ms search. No server. | ChromaDB: needs persistent directory. Pinecone: costs money. |
| **Embedding model** | all-MiniLM-L6-v2 | CPU-only. 384-dim. Fast. Already battle-tested for route clustering. | Larger models too slow on HF Spaces CPU. |
| **Domain models** | Pydantic v2 | Validation at stage boundaries. Clear schema documentation. Python-native. | Dataclasses: no validation. JSON Schema: verbose. |
| **Pipeline orchestration** | Plain Python CLI | 5 linear stages. Airflow/Prefect overhead not justified. | Solo developer — framework learning curve not earned. |
| **PDF export** | ReportLab | Free. Tagged PDF (WCAG accessible). Programmatic layout. | WeasyPrint: can't do tagged PDF. |
| **ML: clustering** | Sentence-transformers + HDBSCAN | Semantic understanding of route descriptions. No preset cluster count needed. | K-means: arbitrary k. LDA: designed for text, not structured features. |
| **ML: anomaly detection** | Isolation Forest | Works well on tabular features. Unsupervised. Fast. | Autoencoders: overkill for this data volume and dimensionality. |
| **ML: prediction** | Random Forest | Interpretable feature importance. Robust to outliers. No hyperparameter sensitivity. | Neural net: black box, unnecessary for ~33k rows and ~8 features. |
| **CI/CD** | GitHub Actions | Free tier (2,000 min/month). Native to GitHub. | Jenkins: self-hosted overhead. CircleCI: less generous free tier. |
| **Logging** | loguru | Structured JSON output. Zero config. Already in ecosystem. | stdlib logging: verbose config. |

---

## 16. What Success Looks Like

### 16.1 For the Platform

| Metric | Target |
|--------|--------|
| Filter response time (p95) | < 100ms |
| Page load time | < 3 seconds |
| Chatbot response time (p95) | < 5 seconds |
| Number consistency (chart vs narrative vs export) | 100% |
| Ground truth validation pass rate | 100% |
| InsightEngine section coverage | 43/43 (100%) |
| Hardcoded narrative text | 0 lines |
| Monthly refresh success rate | > 95% |
| Total deployment cost | £0/month |

### 16.2 For Policy Makers

- A DfT official can look up their region, see coverage metrics, read an evidence-based narrative, and copy the text directly into a business case
- An LTA planner can compare their region to the national average and see the investment required (with BCR) to close the gap
- An academic researcher can download the underlying data and reproduce every metric
- A transport consultant can generate a PDF report for any region to include in a client deliverable

### 16.3 For Credibility

- **Zero inconsistent numbers** across any two pages, charts, narratives, or exports
- **Every metric traceable** to source data through a documented formula in the provenance table
- **Evidence-gated insights** that suppress themselves rather than mislead
- **TAG 2024 compliant** BCR and investment calculations suitable for HM Treasury submission
- **Data currency visible** on every page (source dates, refresh timestamps)

---

**This document describes how to build Aequitas from the intention outward. It does not reference any existing code, bugs, or migration paths. It is a clean-sheet design driven by the problem (fragmented transport data), the audience (policy makers who demand absolute numerical consistency), and the constraints (zero budget, solo developer, HF Spaces deployment).**
