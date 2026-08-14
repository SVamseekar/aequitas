# Architectural Decisions and Hard Rules (Aequitas)

This document records the **intended architectural decisions, data processing invariants, and design patterns** of the Aequitas platform.

---

## 0. £0 stack (locked)
- No paid APIs, Mapbox bills, TRACC, Remix, Conveyal Cloud, StreetLight, Replica, Google Maps Platform, or TravelTime.
- Maps: MapLibre + OSM tiles. Routing: R5/r5py + Geofabrik PBF.
- France deprivation: official F-EDI if free; else documented `aequitas_fr_deprivation_proxy`. Never label a proxy as IMD.

## 1. System Architecture & Invariants

### Decision D01: Pre-computed Warehouse Pattern
- **Decision:** All analytics are pre-computed at build time. The runtime FastAPI backend serves read-only queries from the DuckDB database (`data/aequitas.duckdb`).
- **Constraint:** **NEVER** write live calculations (e.g., dynamic spatial joins, Gini index calculations) inside FastAPI request handlers. All metrics must be read from the DuckDB warehouse tables.

### Decision D02: Deterministic Narratives (InsightEngine)
- **Decision:** The narrative generator (`InsightEngine`) must remain fully deterministic. It uses Jinja2 templates and evidence-gated rules.
- **Constraint:** **NEVER** use LLMs or Gemini calls to generate section narratives. LLMs are reserved exclusively for the chatbot drawer.

### Decision D03: Chatbot Grounding (RAG)
- **Decision:** The chatbot is grounded strictly in the pre-computed warehouse data and policy documents.
- **Constraint:** The chatbot must use the FAISS CPU index for chunk retrieval before querying Gemini. Figures must match the **computed** warehouse for the **active country pack**. Historical `ground_truth.json` is advisory — do not lock Gini at 0.5741.

### Decision D04: Database Schema Governance
- **Constraint:** All migrations and changes to the database schema must be verified using the validation suite (`aequitas validate` / `src/aequitas/validation/`).

---

## 2. Ingestion & Data Quality Rules

### Decision D05: NaPTAN Stops Filtering
- **Constraint:** When ingesting stop locations, only include bus stops (stop types `BCT`, `BCS`, `BCE`). **NEVER** include rail, tram, ferry, or metro stops.
- **Constraint:** Use the status `'active'`, not `'act'` (which yields 0 rows, as confirmed by audit).
- **Constraint:** Always call `reset_index(drop=True)` after filtering stops before constructing KDTrees for spatial lookup.

### Decision D06: BODS Route Counting
- **Constraint:** Always count routes based on `route_id`, not journey patterns, as one route contains multiple journey patterns.
- **Constraint:** De-duplicate routes across regional BODS feeds (same route appearing in multiple feeds must be consolidated into one route).

### Decision D07: Route Length Calculation
- **Constraint:** **NEVER** use BODS `shape_dist_traveled` to compute route lengths, as it is 100% null in the source data. You **MUST** compute route lengths using Haversine formulas.
- **Constraint:** Do **not** drop trips lacking `shape_id` (48.5% of trips). Set `has_geometry = False` instead.

### Decision D08: Large File Chunking
- **Constraint:** Always read BODS `stop_times.txt` in chunks of 1,000,000 rows. **NEVER** load the entire file into memory at once.

---

## 3. Analytics & Formulas

### Decision D09: Deprivation Metrics (IMD)
- **Constraint:** Always use the IMD 2025 dataset with 2021 LSOA boundaries. IMD 2019 is obsolete.

### Decision D10: National Denominator
- **Constraint:** The national population denominator used in calculations **must** always be exactly `56,490,056`. Do **not** use pipeline-filtered or region-specific population numbers as the base for national metrics.
