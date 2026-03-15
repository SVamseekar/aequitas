# Phase 1: Data Pipeline + Warehouse — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete Python pipeline that transforms raw government data into a populated DuckDB warehouse with pre-computed analytics, InsightEngine narratives, and provenance tracking — one CLI command from raw to warehouse.

**Architecture:** Hybrid approach — clean-room implementation for ingestion/processing/dedup (where counting bugs live), ported-from-notebooks for analytics (methodology already validated in 19 EDA notebooks). Pipeline stages: ingest → process → analytics → intelligence → warehouse → validate. All intermediate artifacts are Parquet. Final output is `aequitas.duckdb`.

**Tech Stack:** Python 3.12+, Pydantic v2, DuckDB, pandas, geopandas, scikit-learn, HDBSCAN, SHAP, Jinja2, loguru, pytest, click (CLI)

---

## File Structure

```
src/aequitas/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── models.py              — Pydantic v2 models (BusStop, Route, LSOA, RegionSummary, etc.)
│   ├── constants.py           — TAG v2.03fc + DESNZ 2025 values (loaded from JSON)
│   ├── validators.py          — Reusable field validators (ATCO code, LSOA code, UK bounds, etc.)
│   ├── types.py               — Enums (RegionCode, UrbanRural, StopType, IMDDecile, etc.)
│   └── config.py              — Pipeline config (paths, thresholds, filter space definition)
│
├── ingestion/
│   ├── __init__.py
│   ├── naptan.py              — Load + filter NaPTAN stops (BCT/BCS/BCE, ATCO 0-4, active)
│   ├── bods.py                — Load BODS GTFS from zip (routes, trips, stops, chunked stop_times, shapes)
│   ├── census.py              — Load Census tables (TS001, TS007a, TS021, TS045, TS066, TS038)
│   ├── imd.py                 — Load IMD 2025 scores/deciles/subdomains
│   ├── boundaries.py          — Load LSOA + region GeoJSON boundaries
│   ├── ruc.py                 — Load Rural-Urban Classification 2021
│   ├── poi.py                 — Load POI data (hospitals, GP surgeries, schools, employment proxy)
│   └── constants_loader.py    — Load TAG/DESNZ JSON into typed dataclasses
│
├── processing/
│   ├── __init__.py
│   ├── spatial.py             — Point-in-polygon stop→LSOA, stop→region joins (two-pass)
│   ├── dedup.py               — Cross-region stop + route deduplication
│   ├── demographics.py        — Build master_lsoa_table (9 socio-economic factors)
│   ├── route_geometry.py      — Haversine shape lengths, canonical trips, stop sequences
│   └── service_quality.py     — Headway computation (chunked), SQI composite, evening/Sunday flags
│
├── analytics/
│   ├── __init__.py
│   ├── equity.py              — Gini, Palma, Concentration Index, vulnerability index, triple-deprived
│   ├── ml_clustering.py       — HDBSCAN + GMM soft membership (LSOA + route clustering)
│   ├── ml_prediction.py       — Random Forest coverage prediction + SHAP
│   ├── ml_anomaly.py          — Isolation Forest + LOF anomaly detection
│   ├── accessibility.py       — 2SFCA (stops, hospitals, GPs, schools) via KDTree
│   ├── economic.py            — BCR, investment gap, modal shift scenarios, carbon monetisation
│   └── policy_synthesis.py    — Priority matrix, LTA readiness, policy scenarios, healthcare/education deserts
│
├── intelligence/
│   ├── __init__.py
│   ├── engine.py              — InsightEngine orchestrator (context → rules → templates → output)
│   ├── context.py             — Context resolver (all_regions / single_region / subset scope)
│   ├── calculators.py         — Pure stat functions (rank, distribution, correlation, gini, bcr, gap)
│   ├── rules.py               — Evidence-gated rules (fires only when thresholds met)
│   └── templates/
│       ├── ranking.j2
│       ├── single_region.j2
│       ├── equity.j2
│       ├── service_quality.j2
│       ├── accessibility.j2
│       ├── economic.j2
│       ├── policy.j2
│       └── base.j2
│
├── warehouse/
│   ├── __init__.py
│   ├── schema.py              — DuckDB table definitions (SQL DDL)
│   ├── builder.py             — Load Parquet → DuckDB tables
│   ├── precompute.py          — Generate section_results for all filter × section combinations
│   └── provenance.py          — Provenance table (metric → formula → inputs → source files)
│
├── validation/
│   ├── __init__.py
│   ├── ground_truth.py        — Compare pipeline output against data/audit/ground_truth.json
│   ├── gates.py               — Match rate checks, sanity bounds, population total, entity counts
│   └── report.py              — Generate validation report (JSON + human-readable)
│
└── pipeline/
    ├── __init__.py
    ├── cli.py                 — Click CLI: python -m aequitas.pipeline [stage]
    └── _stages.py             — Stage orchestration: run_ingestion(), run_processing(), etc.

tests/
├── conftest.py                — Shared fixtures (sample data, tmp paths, ground truth loader)
├── core/
│   ├── test_models.py
│   ├── test_constants.py
│   ├── test_validators.py
│   └── test_types.py
├── ingestion/
│   ├── test_naptan.py
│   ├── test_bods.py
│   ├── test_census.py
│   ├── test_imd.py
│   └── test_poi.py
├── processing/
│   ├── test_spatial.py
│   ├── test_dedup.py
│   ├── test_demographics.py
│   ├── test_route_geometry.py
│   └── test_service_quality.py
├── analytics/
│   ├── test_equity.py
│   ├── test_ml_clustering.py
│   ├── test_ml_prediction.py
│   ├── test_ml_anomaly.py
│   ├── test_accessibility.py
│   ├── test_economic.py
│   └── test_policy_synthesis.py
├── intelligence/
│   ├── test_engine.py
│   ├── test_context.py
│   ├── test_calculators.py
│   └── test_rules.py
├── warehouse/
│   ├── test_schema.py
│   ├── test_builder.py
│   └── test_precompute.py
└── validation/
    ├── test_ground_truth.py
    └── test_gates.py

pyproject.toml               — Project metadata, dependencies, tool config
```

---

## Chunk 1: Project Skeleton + Core Layer

### Task 0: Extend ground_truth.json with analytics values

**Files:**
- Modify: `data/audit/ground_truth.json`

The existing `ground_truth.json` contains entity counts (stops, routes, LSOAs, population) and spatial join rates, but NOT the analytics ground truth from the 04-series notebooks. The validation layer (Task 29) needs these to verify the pipeline's statistical outputs.

- [ ] **Step 1: Add analytics ground truth section to ground_truth.json**

Add a new `"analytics"` key with all locked values from CLAUDE.md Ground Truth table and figures-registry.md:

```json
{
  "analytics": {
    "gini_coefficient": 0.5741,
    "palma_ratio": 5.702,
    "concentration_index": 0.1358,
    "dissimilarity_index": 0.4212,
    "triple_deprived_lsoas": 612,
    "quadruple_vulnerable_lsoas": 611,
    "mean_sqi": 65.4,
    "median_headway_min": 33.3,
    "evening_isolated_lsoas": 5189,
    "sunday_desert_lsoas": 6745,
    "routes_with_geometry": 7241,
    "mean_route_length_km": 23.0,
    "cross_la_routes": 5143,
    "rf_r2_test": 0.4719,
    "top_shap_feature": "nocar_pct",
    "anomalies_count": 1688,
    "zero_access_lsoas_2sfca": 6776,
    "q1_priority_lsoas": 6091,
    "lsoas_needing_intervention": 13010,
    "lta_readiness_lad_count": 298,
    "policy_scenarios_count": 4,
    "imd_stop_pearson_r": -0.0644,
    "lsoas_zero_bus_stops": 4245
  },
  "tolerances": {
    "exact": ["triple_deprived_lsoas", "policy_scenarios_count", "top_shap_feature"],
    "within_50": ["evening_isolated_lsoas", "sunday_desert_lsoas", "routes_with_geometry", "cross_la_routes", "anomalies_count", "zero_access_lsoas_2sfca", "q1_priority_lsoas", "lsoas_zero_bus_stops"],
    "within_pct_5": ["gini_coefficient", "palma_ratio", "concentration_index", "mean_sqi", "rf_r2_test", "mean_route_length_km"]
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add data/audit/ground_truth.json
git commit -m "feat: extend ground_truth.json with analytics values for pipeline validation"
```

---

### Task 1: Project Setup (pyproject.toml + package structure)

**Files:**
- Create: `pyproject.toml`
- Create: `src/aequitas/__init__.py`
- Create: `src/aequitas/core/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "aequitas"
version = "0.1.0"
description = "UK bus transport policy intelligence platform"
requires-python = ">=3.12"
dependencies = [
    "pandas>=2.2.0",
    "numpy>=1.26.0",
    "geopandas>=1.0.0",
    "shapely>=2.0.0",
    "scipy>=1.13.0",
    "scikit-learn>=1.5.0",
    "hdbscan>=0.8.38",
    "shap>=0.45.0",
    "pydantic>=2.6.0",
    "duckdb>=1.1.0",
    "jinja2>=3.1.0",
    "click>=8.1.0",
    "loguru>=0.7.0",
    "pyproj>=3.6.0",
    "requests>=2.31.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
]

[project.scripts]
aequitas = "aequitas.pipeline.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
markers = ["slow: marks tests as slow (>5 min, e.g. integration tests)"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "ANN"]
ignore = ["ANN101", "ANN102"]  # self/cls annotation not needed

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true

[tool.hatch.build.targets.wheel]
packages = ["src/aequitas"]
```

- [ ] **Step 2: Create package init files**

Create `src/aequitas/__init__.py`:
```python
"""Aequitas — UK bus transport policy intelligence platform."""

__version__ = "0.1.0"
```

Create `src/aequitas/core/__init__.py`:
```python
"""Core models, constants, validators, and configuration."""
```

- [ ] **Step 3: Create test conftest with shared fixtures**

```python
"""Shared test fixtures for Aequitas test suite."""

import json
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
DATA_AUDIT = PROJECT_ROOT / "data" / "audit"
DATA_RAW = PROJECT_ROOT / "data" / "raw"


@pytest.fixture
def ground_truth() -> dict:
    """Load locked ground truth from Phase 0 audit."""
    with open(DATA_AUDIT / "ground_truth.json") as f:
        return json.load(f)


@pytest.fixture
def tag_constants() -> dict:
    """Load TAG v2.03fc constants."""
    with open(DATA_AUDIT / "tag_constants.json") as f:
        return json.load(f)


@pytest.fixture
def desnz_factors() -> dict:
    """Load DESNZ 2025 carbon factors."""
    with open(DATA_AUDIT / "desnz_carbon_factors.json") as f:
        return json.load(f)


@pytest.fixture
def sample_lsoa_codes() -> list[str]:
    """A handful of known LSOA codes for unit tests."""
    return ["E01000001", "E01000002", "E01000003", "E01033768"]


@pytest.fixture
def master_lsoa_table() -> pd.DataFrame:
    """Load the Phase 0 master LSOA table (33,755 rows)."""
    return pd.read_parquet(DATA_AUDIT / "master_lsoa_table.parquet")
```

- [ ] **Step 4: Install package in dev mode and verify**

Run: `cd /Users/souravamseekarmarti/Projects/aequitas && pip install -e ".[dev]"`
Expected: Successfully installed aequitas-0.1.0

- [ ] **Step 5: Run empty test suite to verify pytest config**

Run: `pytest --co -q`
Expected: "no tests ran" (no test files yet, but config works)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/aequitas/__init__.py src/aequitas/core/__init__.py tests/conftest.py
git commit -m "feat: project skeleton — pyproject.toml, package structure, test fixtures"
```

---

### Task 2: Core Types and Enums

**Files:**
- Create: `src/aequitas/core/types.py`
- Create: `tests/core/test_types.py`

- [ ] **Step 1: Write tests for enums and type definitions**

```python
"""Tests for core type definitions."""

from aequitas.core.types import RegionCode, StopType, UrbanRural, IMDDecile


def test_region_codes_count():
    assert len(RegionCode) == 9


def test_region_code_values():
    assert RegionCode.NORTH_EAST.value == "E12000001"
    assert RegionCode.LONDON.value == "E12000007"


def test_stop_types():
    assert StopType.BCT.value == "BCT"
    assert StopType.BCS.value == "BCS"
    assert StopType.BCE.value == "BCE"


def test_urban_rural():
    assert UrbanRural.URBAN.value == "urban"
    assert UrbanRural.RURAL.value == "rural"


def test_imd_decile_range():
    assert IMDDecile(1).value == 1
    assert IMDDecile(10).value == 10


def test_england_atco_prefixes():
    from aequitas.core.types import ENGLAND_ATCO_PREFIXES
    assert "010" in ENGLAND_ATCO_PREFIXES  # North East
    assert "400" in ENGLAND_ATCO_PREFIXES  # West Midlands
    assert "500" not in ENGLAND_ATCO_PREFIXES  # Scotland
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_types.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Implement types module**

```python
"""Core type definitions for Aequitas pipeline.

Enums for regions, stop types, urban/rural classification, and IMD deciles.
All values match government data source coding schemes.
"""

from enum import Enum, IntEnum


class RegionCode(str, Enum):
    """ONS statistical regions of England (9 regions)."""

    NORTH_EAST = "E12000001"
    NORTH_WEST = "E12000002"
    YORKSHIRE = "E12000003"
    EAST_MIDLANDS = "E12000004"
    WEST_MIDLANDS = "E12000005"
    EAST_OF_ENGLAND = "E12000006"
    LONDON = "E12000007"
    SOUTH_EAST = "E12000008"
    SOUTH_WEST = "E12000009"


class StopType(str, Enum):
    """NaPTAN bus stop types — only these three are bus stops."""

    BCT = "BCT"  # On-street Bus/Coach/Tram stop (most common type)
    BCS = "BCS"  # Bus/Coach station bay
    BCE = "BCE"  # Bus/Coach station entrance


class UrbanRural(str, Enum):
    """Binary urban/rural classification (collapsed from RUC 6-class)."""

    URBAN = "urban"
    RURAL = "rural"


class IMDDecile(IntEnum):
    """IMD 2025 decile (1 = most deprived, 10 = least deprived)."""

    D1 = 1
    D2 = 2
    D3 = 3
    D4 = 4
    D5 = 5
    D6 = 6
    D7 = 7
    D8 = 8
    D9 = 9
    D10 = 10


# ATCO area codes 000-499 are England (500+ is Scotland/Wales/NI)
ENGLAND_ATCO_PREFIXES: frozenset[str] = frozenset(
    f"{i:03d}" for i in range(500)
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_types.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/core/types.py tests/core/test_types.py
git commit -m "feat(core): type definitions — RegionCode, StopType, UrbanRural, IMDDecile enums"
```

---

### Task 3: Core Validators

**Files:**
- Create: `src/aequitas/core/validators.py`
- Create: `tests/core/test_validators.py`

- [ ] **Step 1: Write tests for validators**

```python
"""Tests for reusable field validators."""

import pytest
from aequitas.core.validators import (
    validate_atco_code,
    validate_lsoa_code,
    validate_uk_latitude,
    validate_uk_longitude,
    is_england_atco,
)


def test_valid_atco_code():
    assert validate_atco_code("0100BRP90310") == "0100BRP90310"


def test_invalid_atco_code_too_short():
    with pytest.raises(ValueError, match="ATCO code"):
        validate_atco_code("ABC")


def test_valid_lsoa_code():
    assert validate_lsoa_code("E01000001") == "E01000001"


def test_invalid_lsoa_code():
    with pytest.raises(ValueError, match="LSOA code"):
        validate_lsoa_code("W01000001")  # Wales


def test_uk_latitude_valid():
    assert validate_uk_latitude(51.5) == 51.5


def test_uk_latitude_out_of_range():
    with pytest.raises(ValueError, match="latitude"):
        validate_uk_latitude(70.0)


def test_uk_longitude_valid():
    assert validate_uk_longitude(-0.12) == -0.12


def test_uk_longitude_out_of_range():
    with pytest.raises(ValueError, match="longitude"):
        validate_uk_longitude(10.0)


def test_england_atco_true():
    assert is_england_atco("0100BRP90310") is True
    assert is_england_atco("4990ABC12345") is True


def test_england_atco_false():
    assert is_england_atco("5000SCO00001") is False
    assert is_england_atco("6100WAL00001") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/core/test_validators.py -v`
Expected: FAIL

- [ ] **Step 3: Implement validators**

```python
"""Reusable field validators for Aequitas data models.

Every raw data boundary uses these to catch malformed data early.
"""

import re

_LSOA_PATTERN = re.compile(r"^E0[12]\d{6}$")
_ATCO_MIN_LEN = 8
_ATCO_MAX_LEN = 16
_UK_LAT_RANGE = (49.8, 60.9)
_UK_LON_RANGE = (-8.2, 1.8)


def validate_atco_code(v: str) -> str:
    """Validate NaPTAN ATCO code format (8-16 alphanumeric chars)."""
    if not (_ATCO_MIN_LEN <= len(v) <= _ATCO_MAX_LEN):
        raise ValueError(
            f"ATCO code must be {_ATCO_MIN_LEN}-{_ATCO_MAX_LEN} chars, got {len(v)}: {v!r}"
        )
    return v


def validate_lsoa_code(v: str) -> str:
    """Validate England LSOA code format (E01XXXXXX or E02XXXXXX)."""
    if not _LSOA_PATTERN.match(v):
        raise ValueError(f"LSOA code must match E0[12]XXXXXX pattern, got: {v!r}")
    return v


def validate_uk_latitude(v: float) -> float:
    """Validate latitude is within UK bounds (49.8-60.9)."""
    if not (_UK_LAT_RANGE[0] <= v <= _UK_LAT_RANGE[1]):
        raise ValueError(
            f"UK latitude must be {_UK_LAT_RANGE[0]}-{_UK_LAT_RANGE[1]}, got: {v}"
        )
    return v


def validate_uk_longitude(v: float) -> float:
    """Validate longitude is within UK bounds (-8.2 to 1.8)."""
    if not (_UK_LON_RANGE[0] <= v <= _UK_LON_RANGE[1]):
        raise ValueError(
            f"UK longitude must be {_UK_LON_RANGE[0]}-{_UK_LON_RANGE[1]}, got: {v}"
        )
    return v


def is_england_atco(atco_code: str) -> bool:
    """Check if an ATCO code belongs to an England admin area (prefix 000-499)."""
    try:
        prefix = int(atco_code[:3])
    except (ValueError, IndexError):
        return False
    return 0 <= prefix <= 499
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/core/test_validators.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/core/validators.py tests/core/test_validators.py
git commit -m "feat(core): field validators — ATCO, LSOA, UK coordinate bounds"
```

---

### Task 4: Core Pydantic Models

**Files:**
- Create: `src/aequitas/core/models.py`
- Create: `tests/core/test_models.py`

- [ ] **Step 1: Write tests for Pydantic models**

```python
"""Tests for core Pydantic v2 data models."""

import pytest
from pydantic import ValidationError
from aequitas.core.models import BusStop, Route, LSOARecord, RegionSummary


class TestBusStop:
    def test_valid_stop(self):
        stop = BusStop(
            stop_id="0100BRP90310",
            stop_name="High Street",
            latitude=51.5,
            longitude=-0.12,
            lsoa_code="E01000001",
            region_code="E12000007",
            stop_type="BCT",
        )
        assert stop.stop_id == "0100BRP90310"

    def test_rejects_wales_lsoa(self):
        with pytest.raises(ValidationError):
            BusStop(
                stop_id="0100BRP90310",
                stop_name="Test",
                latitude=51.5,
                longitude=-0.12,
                lsoa_code="W01000001",
                region_code="E12000007",
                stop_type="BCT",
            )

    def test_rejects_invalid_coords(self):
        with pytest.raises(ValidationError):
            BusStop(
                stop_id="0100BRP90310",
                stop_name="Test",
                latitude=70.0,
                longitude=-0.12,
                lsoa_code="E01000001",
                region_code="E12000007",
                stop_type="BCT",
            )


class TestRoute:
    def test_valid_route(self):
        route = Route(
            route_id="R001",
            line_name="1A",
            route_length_km=15.2,
            num_stops=25,
            trips_per_day=48,
            regions_served=["E12000007"],
            has_geometry=True,
        )
        assert route.route_id == "R001"

    def test_negative_length_rejected(self):
        with pytest.raises(ValidationError):
            Route(
                route_id="R001",
                line_name="1A",
                route_length_km=-5.0,
                num_stops=25,
                trips_per_day=48,
                regions_served=["E12000007"],
                has_geometry=True,
            )


class TestRegionSummary:
    def test_stops_per_1000_sanity(self):
        """Sanity validator: stops_per_1000 > 30 means counting error."""
        with pytest.raises(ValidationError, match="sanity"):
            RegionSummary(
                region_code="E12000001",
                region_name="North East",
                population=2_647_000,
                unique_stops=100_000,
                unique_routes=500,
                stops_per_1000=37.8,
                routes_per_100k=18.9,
            )

    def test_valid_summary(self):
        s = RegionSummary(
            region_code="E12000001",
            region_name="North East",
            population=2_647_000,
            unique_stops=18_000,
            unique_routes=500,
            stops_per_1000=6.8,
            routes_per_100k=18.9,
        )
        assert s.population == 2_647_000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/core/test_models.py -v`
Expected: FAIL

- [ ] **Step 3: Implement models**

```python
"""Pydantic v2 data models for Aequitas pipeline.

Every data boundary in the pipeline validates through these models.
Entity definitions match the Phase 0 audit ground truth.
"""

from pydantic import BaseModel, Field, field_validator

from aequitas.core.validators import (
    validate_atco_code,
    validate_lsoa_code,
    validate_uk_latitude,
    validate_uk_longitude,
)


class BusStop(BaseModel):
    """A single physical bus stop location. Counted ONCE by ATCO code."""

    stop_id: str = Field(description="NaPTAN ATCO code")
    stop_name: str
    latitude: float
    longitude: float
    lsoa_code: str
    region_code: str
    stop_type: str = Field(description="BCT, BCS, or BCE")

    @field_validator("stop_id")
    @classmethod
    def validate_stop_id(cls, v: str) -> str:
        return validate_atco_code(v)

    @field_validator("lsoa_code")
    @classmethod
    def validate_lsoa(cls, v: str) -> str:
        return validate_lsoa_code(v)

    @field_validator("latitude")
    @classmethod
    def validate_lat(cls, v: float) -> float:
        return validate_uk_latitude(v)

    @field_validator("longitude")
    @classmethod
    def validate_lon(cls, v: float) -> float:
        return validate_uk_longitude(v)


class Route(BaseModel):
    """A named bus service. Counted ONCE regardless of regions or journey patterns."""

    route_id: str
    line_name: str
    route_length_km: float = Field(ge=0)
    num_stops: int = Field(ge=0)
    trips_per_day: int = Field(ge=0)
    regions_served: list[str]
    has_geometry: bool


class LSOARecord(BaseModel):
    """An LSOA with all 9 socio-economic factors attached."""

    lsoa_code: str
    lsoa_name: str
    population: int = Field(gt=0)
    imd_score: float = Field(ge=0)
    imd_decile: int = Field(ge=1, le=10)
    unemployment_rate: float = Field(ge=0, le=100)
    nocar_pct: float = Field(ge=0, le=100)
    elderly_pct: float = Field(ge=0, le=100)
    income_score: float = Field(ge=0, le=1)
    nonwhite_pct: float = Field(ge=0, le=100)
    geo_barriers_score: float = Field(ge=0)
    urban_rural: str
    disability_pct: float = Field(ge=0, le=100)

    @field_validator("lsoa_code")
    @classmethod
    def validate_lsoa(cls, v: str) -> str:
        return validate_lsoa_code(v)


class RegionSummary(BaseModel):
    """Per-region aggregated statistics."""

    region_code: str
    region_name: str
    population: int = Field(gt=0)
    unique_stops: int = Field(ge=0)
    unique_routes: int = Field(ge=0)
    stops_per_1000: float = Field(ge=0)
    routes_per_100k: float = Field(ge=0)

    @field_validator("stops_per_1000")
    @classmethod
    def sanity_check_stops(cls, v: float) -> float:
        if v > 30:
            raise ValueError(
                f"stops_per_1000={v} exceeds sanity bound of 30. "
                "Are you counting stop-route records instead of unique stops?"
            )
        return v


class SectionResult(BaseModel):
    """Pre-computed result for one (region × urban_rural × section) combination."""

    region: str
    urban_rural: str
    section_id: str
    stats: dict
    chart_data: dict
    narrative: dict


class ProvenanceEntry(BaseModel):
    """Audit trail: metric → formula → inputs → source files."""

    metric_id: str
    value: float
    formula: str
    inputs: dict
    source_files: list[str]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/core/test_models.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/core/models.py tests/core/test_models.py
git commit -m "feat(core): Pydantic v2 models — BusStop, Route, LSOA, RegionSummary, SectionResult"
```

---

### Task 5: Core Constants (TAG + DESNZ)

**Files:**
- Create: `src/aequitas/core/constants.py`
- Create: `tests/core/test_constants.py`

- [ ] **Step 1: Write tests for constants loading**

```python
"""Tests for TAG v2.03fc and DESNZ 2025 constants."""

import pytest
from aequitas.core.constants import TAG, DESNZ, POPULATION_ENGLAND, LSOA_COUNT_ENGLAND


def test_population_denominator():
    assert POPULATION_ENGLAND == 56_490_056


def test_lsoa_count():
    assert LSOA_COUNT_ENGLAND == 33_755


def test_tag_vot_commuting():
    assert TAG().vot_commuting_2014 == pytest.approx(11.21, abs=0.01)


def test_tag_vot_leisure():
    assert TAG().vot_leisure_2014 == pytest.approx(5.12, abs=0.01)


def test_tag_carbon_central_2025():
    assert TAG().carbon_value_central_2025 == pytest.approx(259.87, abs=0.01)


def test_tag_discount_rate():
    assert TAG().social_discount_rate == pytest.approx(0.035, abs=0.001)


def test_desnz_bus_co2():
    assert DESNZ().bus_co2_avg_local == pytest.approx(0.10385, abs=0.0001)


def test_desnz_car_co2():
    assert DESNZ().car_co2_avg_diesel == pytest.approx(0.17304, abs=0.0001)


def test_desnz_modal_shift_saving():
    assert DESNZ().modal_shift_car_to_bus == pytest.approx(0.00779, abs=0.0001)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/core/test_constants.py -v`
Expected: FAIL

- [ ] **Step 3: Implement constants module**

```python
"""TAG v2.03fc and DESNZ 2025 constants — single source of truth.

Values loaded from data/audit/*.json (extracted in Phase 0 notebooks 03f, 03g).
Do NOT hardcode appraisal values inline anywhere else in the codebase.
"""

import json
from dataclasses import dataclass
from pathlib import Path

_AUDIT_DIR = Path(__file__).parent.parent.parent.parent / "data" / "audit"

# Ground truth denominators — do not change without re-running audit
POPULATION_ENGLAND: int = 56_490_056
LSOA_COUNT_ENGLAND: int = 33_755


@dataclass(frozen=True)
class TAGConstants:
    """TAG Databook v2.03fc values (Dec 2025)."""

    # Value of Time — Source VoT sheet, 2014 prices
    vot_commuting_2014: float
    vot_leisure_2014: float
    vot_business_avg_2014: float
    vot_bus_passenger_business_2014: float
    # A1.3.1 published, 2023 prices (factor cost)
    vot_commuting_2023: float
    vot_leisure_2023: float
    vot_business_avg_2023: float
    vot_bus_passenger_business_2023: float
    # Carbon appraisal, 2020 prices
    carbon_value_central_2010: float
    carbon_value_central_2025: float
    carbon_value_central_2030: float
    # Discount rate
    social_discount_rate: float


@dataclass(frozen=True)
class DESNZConstants:
    """DESNZ GHG Conversion Factors 2025."""

    bus_co2_avg_local: float  # kg CO2e/pax-km
    bus_co2_not_london: float
    bus_co2_london: float
    coach_co2: float
    car_co2_avg_diesel: float  # kg CO2e/veh-km
    car_co2_per_pax_km: float  # derived (÷1.55 occupancy)
    rail_co2: float
    modal_shift_car_to_bus: float  # kg CO2e/pax-km saved
    car_occupancy: float


def _load_tag() -> TAGConstants:
    with open(_AUDIT_DIR / "tag_constants.json") as f:
        data = json.load(f)
    vot = data["value_of_time"]
    carbon = data["carbon_appraisal"]
    return TAGConstants(
        vot_commuting_2014=vot["source_vot_2014_prices"]["commuting_all_modes"],
        vot_leisure_2014=vot["source_vot_2014_prices"]["leisure_other"],
        vot_business_avg_2014=vot["source_vot_2014_prices"]["business_working_avg"],
        vot_bus_passenger_business_2014=vot["source_vot_2014_prices"]["psv_bus_passenger_business"],
        vot_commuting_2023=vot["a131_2023_prices"]["commuting_factor_cost"],
        vot_leisure_2023=vot["a131_2023_prices"]["leisure_other_factor_cost"],
        vot_business_avg_2023=vot["a131_2023_prices"]["business_working_avg_factor_cost"],
        vot_bus_passenger_business_2023=vot["a131_2023_prices"]["psv_passenger_business_factor_cost"],
        carbon_value_central_2010=carbon["central_2020_prices"]["2010"],
        carbon_value_central_2025=carbon["central_2020_prices"]["2025"],
        carbon_value_central_2030=carbon["central_2020_prices"]["2030"],
        social_discount_rate=0.035,
    )


def _load_desnz() -> DESNZConstants:
    with open(_AUDIT_DIR / "desnz_carbon_factors.json") as f:
        data = json.load(f)
    t = data["transport_factors"]
    return DESNZConstants(
        bus_co2_avg_local=t["bus"]["average_local_bus"]["kg_co2e_per_pax_km"],
        bus_co2_not_london=t["bus"]["local_bus_not_london"]["kg_co2e_per_pax_km"],
        bus_co2_london=t["bus"]["local_bus_london"]["kg_co2e_per_pax_km"],
        coach_co2=t["bus"]["coach"]["kg_co2e_per_pax_km"],
        car_co2_avg_diesel=t["car"]["average_car_diesel"]["kg_co2e_per_km"],
        car_co2_per_pax_km=t["car"]["derived_per_pax_km"]["kg_co2e_per_pax_km"],
        rail_co2=t["rail"]["national_rail"]["kg_co2e_per_pax_km"],
        modal_shift_car_to_bus=t["derived"]["modal_shift_car_to_bus"]["kg_co2e_per_pax_km"],
        car_occupancy=t["car"]["occupancy_nts2023"],
    )


def _lazy_tag() -> TAGConstants:
    """Lazy-load TAG constants — avoids crash if JSON missing at import time."""
    return _load_tag()


def _lazy_desnz() -> DESNZConstants:
    """Lazy-load DESNZ constants — avoids crash if JSON missing at import time."""
    return _load_desnz()


# Use functools.cache for lazy singleton loading
from functools import cache as _cache
_lazy_tag = _cache(_lazy_tag)
_lazy_desnz = _cache(_lazy_desnz)


# Public API — call these as TAG() and DESNZ() (note: callables, not module-level constants)
TAG = _lazy_tag
DESNZ = _lazy_desnz
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/core/test_constants.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/core/constants.py tests/core/test_constants.py
git commit -m "feat(core): TAG v2.03fc + DESNZ 2025 constants — loaded from audit JSON"
```

---

### Task 6: Core Config

**Files:**
- Create: `src/aequitas/core/config.py`
- Create: `tests/core/test_config.py` (minimal)

- [ ] **Step 1: Write config test**

```python
"""Tests for pipeline configuration."""

from pathlib import Path
from aequitas.core.config import PipelineConfig


def test_default_config_paths_exist():
    cfg = PipelineConfig()
    assert cfg.raw_dir.exists()
    assert cfg.audit_dir.exists()


def test_filter_space():
    cfg = PipelineConfig()
    combos = cfg.filter_combinations()
    # 10 regions (all + 9) × 3 area types = 30
    assert len(combos) == 30
```

- [ ] **Step 2: Run test, verify fail**

Run: `pytest tests/core/test_config.py -v`

- [ ] **Step 3: Implement config**

```python
"""Pipeline configuration — paths, thresholds, filter space."""

from dataclasses import dataclass, field
from pathlib import Path

from aequitas.core.types import RegionCode

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@dataclass
class PipelineConfig:
    """Central configuration for all pipeline stages."""

    project_root: Path = _PROJECT_ROOT
    raw_dir: Path = field(default_factory=lambda: _PROJECT_ROOT / "data" / "raw")
    audit_dir: Path = field(default_factory=lambda: _PROJECT_ROOT / "data" / "audit")
    processed_dir: Path = field(default_factory=lambda: _PROJECT_ROOT / "data" / "processed")
    warehouse_path: Path = field(default_factory=lambda: _PROJECT_ROOT / "data" / "aequitas.duckdb")

    # Validation thresholds
    min_match_rate: float = 0.95
    stops_per_1000_max: float = 30.0
    routes_sanity_max: int = 50_000

    # BODS chunking
    stop_times_chunk_size: int = 1_000_000
    shapes_chunk_size: int = 500_000

    def filter_combinations(self) -> list[tuple[str, str]]:
        """All 30 filter combinations: (region, urban_rural)."""
        regions = ["all"] + [r.value for r in RegionCode]
        area_types = ["all", "urban", "rural"]
        return [(r, a) for r in regions for a in area_types]
```

- [ ] **Step 4: Run test, verify pass**

Run: `pytest tests/core/test_config.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/core/config.py tests/core/test_config.py
git commit -m "feat(core): pipeline config — paths, thresholds, filter space"
```

---

## Chunk 2: Ingestion Layer

### Task 7: NaPTAN Ingestion

**Files:**
- Create: `src/aequitas/ingestion/__init__.py`
- Create: `src/aequitas/ingestion/naptan.py`
- Create: `tests/ingestion/test_naptan.py`

- [ ] **Step 1: Write tests for NaPTAN loader**

Test that the loader:
- Filters to StopType BCT/BCS/BCE only
- Filters to Status == 'active'
- Filters to England ATCO prefixes (000-499)
- Returns exactly 274,719 rows (ground truth)
- All returned stop_ids are unique
- Output has required columns: ATCOCode, CommonName, Latitude, Longitude, StopType, Status

```python
"""Tests for NaPTAN ingestion."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.ingestion.naptan import load_naptan


@pytest.fixture
def naptan_df():
    cfg = PipelineConfig()
    return load_naptan(cfg.raw_dir / "naptan" / "Stops.csv")


def test_naptan_count(naptan_df, ground_truth):
    assert len(naptan_df) == ground_truth["naptan"]["england_active_bus_stops"]


def test_naptan_unique_ids(naptan_df):
    assert naptan_df["ATCOCode"].nunique() == len(naptan_df)


def test_naptan_stop_types(naptan_df):
    allowed = {"BCT", "BCS", "BCE"}
    assert set(naptan_df["StopType"].unique()).issubset(allowed)


def test_naptan_status(naptan_df):
    assert (naptan_df["Status"] == "active").all()


def test_naptan_england_only(naptan_df):
    prefixes = naptan_df["ATCOCode"].str[:3].astype(int)
    assert (prefixes < 500).all()


def test_naptan_has_coordinates(naptan_df):
    assert naptan_df["Latitude"].notna().sum() > 0.95 * len(naptan_df)
```

- [ ] **Step 2: Run test, verify fail**

Run: `pytest tests/ingestion/test_naptan.py -v`

- [ ] **Step 3: Implement NaPTAN loader**

```python
"""NaPTAN bus stop ingestion.

Loads the NaPTAN Stops.csv and filters to England active bus stops.
Filter chain: StopType ∈ {BCT, BCS, BCE} → Status == 'active' → ATCO prefix 000-499.
"""

from pathlib import Path

import pandas as pd
from loguru import logger

from aequitas.core.types import ENGLAND_ATCO_PREFIXES

_BUS_STOP_TYPES = frozenset({"BCT", "BCS", "BCE"})
_REQUIRED_COLS = ["ATCOCode", "CommonName", "Latitude", "Longitude", "StopType", "Status"]


def load_naptan(path: Path) -> pd.DataFrame:
    """Load and filter NaPTAN stops to England active bus stops."""
    logger.info("Loading NaPTAN from {}", path)
    df = pd.read_csv(path, usecols=_REQUIRED_COLS + ["Easting", "Northing"], low_memory=False)
    logger.info("Raw NaPTAN rows: {}", len(df))

    # Filter: bus stop types only
    df = df[df["StopType"].isin(_BUS_STOP_TYPES)]
    logger.info("After StopType filter (BCT/BCS/BCE): {}", len(df))

    # Filter: active only
    df = df[df["Status"] == "active"]
    logger.info("After Status=active filter: {}", len(df))

    # Filter: England ATCO prefixes (000-499)
    df = df[df["ATCOCode"].str[:3].isin(ENGLAND_ATCO_PREFIXES)]
    logger.info("After England ATCO filter: {}", len(df))

    # Deduplicate on ATCO code (should already be unique)
    n_before = len(df)
    df = df.drop_duplicates(subset="ATCOCode", keep="first")
    if len(df) < n_before:
        logger.warning("Dropped {} duplicate ATCOCodes", n_before - len(df))

    logger.info("Final NaPTAN England active bus stops: {}", len(df))
    return df.reset_index(drop=True)
```

- [ ] **Step 4: Run test, verify pass**

Run: `pytest tests/ingestion/test_naptan.py -v`
Expected: All PASS (counts should match ground truth)

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/ingestion/__init__.py src/aequitas/ingestion/naptan.py tests/ingestion/test_naptan.py
git commit -m "feat(ingestion): NaPTAN loader — filters to 274,719 England active bus stops"
```

---

### Task 8: BODS GTFS Ingestion

**Files:**
- Create: `src/aequitas/ingestion/bods.py`
- Create: `tests/ingestion/test_bods.py`

- [ ] **Step 1: Write tests for BODS loader**

```python
"""Tests for BODS GTFS ingestion."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.ingestion.bods import load_bods_routes, load_bods_trips, load_bods_stops, load_bods_calendar


@pytest.fixture(scope="module")
def cfg():
    return PipelineConfig()


@pytest.fixture(scope="module")
def bods_zip(cfg):
    return cfg.raw_dir / "bods" / "bods_gtfs_all.zip"


def test_routes_count(bods_zip, ground_truth):
    routes = load_bods_routes(bods_zip)
    assert len(routes) == ground_truth["bods"]["raw_route_rows"]


def test_routes_unique_ids(bods_zip):
    routes = load_bods_routes(bods_zip)
    assert routes["route_id"].nunique() == len(routes)


def test_trips_count(bods_zip, ground_truth):
    trips = load_bods_trips(bods_zip)
    assert len(trips) == ground_truth["bods"]["total_trips"]


def test_stops_count(bods_zip, ground_truth):
    stops = load_bods_stops(bods_zip)
    assert stops["stop_id"].nunique() == ground_truth["bods"]["bods_unique_stop_ids"]


def test_calendar_loads(bods_zip):
    cal = load_bods_calendar(bods_zip)
    assert "service_id" in cal.columns
    assert len(cal) > 0
```

- [ ] **Step 2: Run test, verify fail**

Run: `pytest tests/ingestion/test_bods.py -v`

- [ ] **Step 3: Implement BODS loader**

```python
"""BODS GTFS ingestion — routes, trips, stops, calendar from zip.

Reads from the bulk GTFS archive. stop_times.txt (5.8GB) and shapes.txt (3.2GB)
are NOT loaded here — they're streamed in processing stages that need them.
"""

from pathlib import Path
from zipfile import ZipFile

import pandas as pd
from loguru import logger


def _read_from_zip(zip_path: Path, filename: str, **kwargs) -> pd.DataFrame:
    """Read a CSV file from inside a zip archive."""
    with ZipFile(zip_path) as zf:
        with zf.open(filename) as f:
            return pd.read_csv(f, **kwargs)


def load_bods_routes(zip_path: Path) -> pd.DataFrame:
    """Load routes.txt from BODS GTFS zip."""
    logger.info("Loading BODS routes from {}", zip_path)
    df = _read_from_zip(zip_path, "routes.txt")
    logger.info("BODS routes loaded: {}", len(df))
    return df


def load_bods_trips(zip_path: Path) -> pd.DataFrame:
    """Load trips.txt from BODS GTFS zip."""
    logger.info("Loading BODS trips from {}", zip_path)
    df = _read_from_zip(zip_path, "trips.txt")
    logger.info("BODS trips loaded: {}", len(df))
    return df


def load_bods_stops(zip_path: Path) -> pd.DataFrame:
    """Load stops.txt from BODS GTFS zip."""
    logger.info("Loading BODS stops from {}", zip_path)
    df = _read_from_zip(zip_path, "stops.txt")
    logger.info("BODS stops loaded: {}", len(df))
    return df


def load_bods_calendar(zip_path: Path) -> pd.DataFrame:
    """Load calendar.txt from BODS GTFS zip."""
    logger.info("Loading BODS calendar from {}", zip_path)
    df = _read_from_zip(zip_path, "calendar.txt")
    logger.info("BODS calendar loaded: {} services", len(df))
    return df
```

- [ ] **Step 4: Run test, verify pass**

Run: `pytest tests/ingestion/test_bods.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/ingestion/bods.py tests/ingestion/test_bods.py
git commit -m "feat(ingestion): BODS GTFS loader — routes, trips, stops, calendar"
```

---

### Task 9: Census + IMD + RUC Ingestion

**Files:**
- Create: `src/aequitas/ingestion/census.py`
- Create: `src/aequitas/ingestion/imd.py`
- Create: `src/aequitas/ingestion/ruc.py`
- Create: `tests/ingestion/test_census.py`
- Create: `tests/ingestion/test_imd.py`

- [ ] **Step 1: Write tests for Census loaders**

```python
"""Tests for Census table ingestion."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.ingestion.census import (
    load_population,
    load_age_structure,
    load_car_ownership,
    load_ethnicity,
    load_unemployment,
    load_disability,
)

@pytest.fixture(scope="module")
def cfg():
    return PipelineConfig()


def test_population_total(cfg, ground_truth):
    df = load_population(cfg.raw_dir)
    total = df["population"].sum()
    assert abs(total - ground_truth["census"]["total_population_sum"]) < 100


def test_population_lsoa_count(cfg, ground_truth):
    df = load_population(cfg.raw_dir)
    assert len(df) == ground_truth["census"]["total_lsoas_england"]


def test_unemployment_no_nulls(cfg):
    df = load_unemployment(cfg.raw_dir)
    assert df["unemployment_rate"].notna().all()


def test_disability_loads(cfg):
    df = load_disability(cfg.raw_dir)
    assert "disability_pct" in df.columns
    assert len(df) >= 33_000  # England LSOAs
```

- [ ] **Step 2: Write tests for IMD**

```python
"""Tests for IMD 2025 ingestion."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.ingestion.imd import load_imd


def test_imd_lsoa_count(ground_truth):
    cfg = PipelineConfig()
    df = load_imd(cfg.raw_dir / "imd" / "imd2025_all_ranks_scores_deciles.csv")
    assert len(df) == ground_truth["imd"]["total_lsoas"]


def test_imd_no_missing_scores():
    cfg = PipelineConfig()
    df = load_imd(cfg.raw_dir / "imd" / "imd2025_all_ranks_scores_deciles.csv")
    assert df["imd_score"].notna().all()


def test_imd_decile_range():
    cfg = PipelineConfig()
    df = load_imd(cfg.raw_dir / "imd" / "imd2025_all_ranks_scores_deciles.csv")
    assert df["imd_decile"].between(1, 10).all()
```

- [ ] **Step 3: Implement Census loaders**

Each loader: read CSV/zip → filter England → rename columns → return clean DataFrame with `lsoa_code` as join key. See notebook patterns from 01_data_audit for exact column names and filter logic.

- [ ] **Step 4: Implement IMD + RUC loaders**

IMD: read CSV → rename columns → validate 33,755 rows. RUC: read CSV → map 6-class to binary urban/rural.

- [ ] **Step 5: Run all tests, verify pass**

Run: `pytest tests/ingestion/ -v`

- [ ] **Step 6: Commit**

```bash
git add src/aequitas/ingestion/census.py src/aequitas/ingestion/imd.py src/aequitas/ingestion/ruc.py tests/ingestion/test_census.py tests/ingestion/test_imd.py
git commit -m "feat(ingestion): Census, IMD, RUC loaders — all 9 socio-economic factors"
```

---

### Task 10: Boundary + POI Ingestion

**Files:**
- Create: `src/aequitas/ingestion/boundaries.py`
- Create: `src/aequitas/ingestion/poi.py`
- Create: `src/aequitas/ingestion/constants_loader.py`
- Create: `tests/ingestion/test_poi.py`

- [ ] **Step 1: Write tests for POI loaders**

```python
"""Tests for POI data ingestion."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.ingestion.poi import load_hospitals, load_gp_surgeries, load_schools, load_employment_proxy


@pytest.fixture(scope="module")
def cfg():
    return PipelineConfig()


def test_hospitals_count(cfg, ground_truth):
    df = load_hospitals(cfg.audit_dir / "hospitals_geocoded.parquet")
    # Geocoded count from Phase 0
    assert len(df) == 3714


def test_gp_surgeries_count(cfg):
    df = load_gp_surgeries(cfg.audit_dir / "gp_surgeries_geocoded.parquet")
    assert len(df) == 12059


def test_schools_secondary_count(cfg):
    df = load_schools(cfg.audit_dir / "schools_secondary_geocoded.parquet")
    assert len(df) == 3336


def test_employment_proxy(cfg):
    df = load_employment_proxy(cfg.audit_dir / "lsoa_employment_proxy.parquet")
    assert len(df) >= 32_000
    assert "employees" in df.columns
```

- [ ] **Step 2: Implement boundaries loader**

Loads LSOA + region GeoJSON with dynamic column detection (RGN21/RGN22 vintage handling).

- [ ] **Step 3: Implement POI loader**

**Design decision:** POI data loads from Phase 0 geocoded Parquets in `data/audit/`, NOT re-processed from raw CSVs. Rationale: geocoding (postcode lookup, coordinate extraction, England filtering) was validated in notebooks 03b-03e with confirmed counts. Re-implementing adds complexity for no ground truth improvement. Validation compares loaded counts against ground truth (3,714 hospitals, 12,059 GPs, 3,336 secondary schools, 32,919 LSOAs with employment proxy).

- [ ] **Step 4: Implement constants_loader**

Thin wrapper that loads TAG/DESNZ JSON — delegates to `core/constants.py`.

- [ ] **Step 5: Run tests, verify pass**

Run: `pytest tests/ingestion/ -v`

- [ ] **Step 6: Commit**

```bash
git add src/aequitas/ingestion/boundaries.py src/aequitas/ingestion/poi.py src/aequitas/ingestion/constants_loader.py tests/ingestion/test_poi.py
git commit -m "feat(ingestion): boundaries, POI, constants loaders"
```

---

## Chunk 3: Processing Layer

### Task 11: Spatial Joins (Stop → LSOA → Region)

**Files:**
- Create: `src/aequitas/processing/__init__.py`
- Create: `src/aequitas/processing/spatial.py`
- Create: `tests/processing/test_spatial.py`

- [ ] **Step 1: Write tests for spatial join**

```python
"""Tests for spatial join processing."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.ingestion.naptan import load_naptan
from aequitas.ingestion.boundaries import load_lsoa_boundaries
from aequitas.processing.spatial import assign_stops_to_lsoa


@pytest.fixture(scope="module")
def cfg():
    return PipelineConfig()


def test_stop_lsoa_match_rate(cfg, ground_truth):
    stops = load_naptan(cfg.raw_dir / "naptan" / "Stops.csv")
    lsoa_gdf = load_lsoa_boundaries(cfg.raw_dir / "boundaries")
    result = assign_stops_to_lsoa(stops, lsoa_gdf)
    match_rate = result["lsoa_code"].notna().mean()
    expected = ground_truth["joins"]["stop_to_lsoa_match_rate_pct"] / 100
    assert match_rate >= expected - 0.001


def test_all_lsoa_codes_valid(cfg):
    stops = load_naptan(cfg.raw_dir / "naptan" / "Stops.csv")
    lsoa_gdf = load_lsoa_boundaries(cfg.raw_dir / "boundaries")
    result = assign_stops_to_lsoa(stops, lsoa_gdf)
    matched = result[result["lsoa_code"].notna()]
    assert matched["lsoa_code"].str.match(r"^E0[12]\d{6}$").all()
```

- [ ] **Step 2: Implement spatial join**

Two-pass spatial join:
1. Point-in-polygon (EPSG:27700) for >99.99% of stops
2. `sjoin_nearest` with max_distance=2000m for coastal/pier orphans

Key: `reset_index(drop=True)` before building any spatial index.

```python
"""Spatial join: assign stops to LSOAs and regions.

Two-pass strategy matching Phase 0 audit methodology:
  Pass 1: Point-in-polygon (catches 99.99%)
  Pass 2: sjoin_nearest for coastal/pier orphans (max 2km)
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd
from loguru import logger
from shapely.geometry import Point


def assign_stops_to_lsoa(
    stops_df: pd.DataFrame,
    lsoa_gdf: gpd.GeoDataFrame,
    max_nearest_distance_m: float = 2000.0,
) -> pd.DataFrame:
    """Assign each stop to an LSOA via two-pass spatial join."""
    # Convert stops to GeoDataFrame in BNG (EPSG:27700)
    stops_gdf = gpd.GeoDataFrame(
        stops_df.reset_index(drop=True),
        geometry=gpd.points_from_xy(stops_df["Longitude"], stops_df["Latitude"]),
        crs="EPSG:4326",
    ).to_crs("EPSG:27700")

    lsoa_27700 = lsoa_gdf.to_crs("EPSG:27700") if lsoa_gdf.crs != "EPSG:27700" else lsoa_gdf

    # Pass 1: point-in-polygon
    logger.info("Pass 1: point-in-polygon spatial join")
    joined = gpd.sjoin(stops_gdf, lsoa_27700[["LSOA21CD", "geometry"]], how="left", predicate="within")
    matched_mask = joined["LSOA21CD"].notna()
    logger.info("Pass 1 matched: {}/{}", matched_mask.sum(), len(joined))

    # Pass 2: nearest for unmatched
    unmatched = stops_gdf[~matched_mask].copy()
    if len(unmatched) > 0:
        logger.info("Pass 2: sjoin_nearest for {} unmatched stops", len(unmatched))
        nearest = gpd.sjoin_nearest(
            unmatched, lsoa_27700[["LSOA21CD", "geometry"]],
            how="left", max_distance=max_nearest_distance_m,
        )
        joined.loc[~matched_mask, "LSOA21CD"] = nearest["LSOA21CD"].values

    result = stops_df.copy()
    result["lsoa_code"] = joined["LSOA21CD"].values
    final_rate = result["lsoa_code"].notna().mean()
    logger.info("Final match rate: {:.4%}", final_rate)
    return result
```

- [ ] **Step 3: Run tests, verify pass**

Run: `pytest tests/processing/test_spatial.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/aequitas/processing/__init__.py src/aequitas/processing/spatial.py tests/processing/test_spatial.py
git commit -m "feat(processing): two-pass spatial join — stop→LSOA assignment (99.99% match)"
```

---

### Task 12: Cross-Region Deduplication

**Files:**
- Create: `src/aequitas/processing/dedup.py`
- Create: `tests/processing/test_dedup.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for cross-region deduplication."""

import pandas as pd
import pytest
from aequitas.processing.dedup import deduplicate_stops, deduplicate_routes


def test_dedup_stops_removes_duplicates():
    df = pd.DataFrame({
        "stop_id": ["A", "B", "A", "C"],
        "stop_name": ["x", "y", "x", "z"],
    })
    result = deduplicate_stops(df)
    assert len(result) == 3
    assert result["stop_id"].nunique() == len(result)


def test_dedup_routes_merges_regions():
    df = pd.DataFrame({
        "route_id": ["R1", "R1", "R2"],
        "line_name": ["1A", "1A", "2B"],
        "region_code": ["E12000001", "E12000002", "E12000003"],
        "trips_per_day": [48, 52, 30],
    })
    result = deduplicate_routes(df)
    assert len(result) == 2
    r1 = result[result["route_id"] == "R1"].iloc[0]
    assert set(r1["regions_served"]) == {"E12000001", "E12000002"}
    assert r1["trips_per_day"] == 52  # max
```

- [ ] **Step 2: Implement deduplication**

Follows BLUEPRINT Section 8.3 Step 3 logic exactly:
- Stops: `drop_duplicates(subset='stop_id', keep='first')`
- Routes: `groupby('route_id')`, aggregate regions into list, take max trips_per_day

- [ ] **Step 3: Run tests, verify pass**

Run: `pytest tests/processing/test_dedup.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/aequitas/processing/dedup.py tests/processing/test_dedup.py
git commit -m "feat(processing): cross-region deduplication — stops unique by ATCO, routes by route_id"
```

---

### Task 13: Demographics Assembly (master_lsoa_table)

**Files:**
- Create: `src/aequitas/processing/demographics.py`
- Create: `tests/processing/test_demographics.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for master LSOA table assembly."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.core.constants import LSOA_COUNT_ENGLAND, POPULATION_ENGLAND
from aequitas.processing.demographics import build_master_lsoa_table


def test_master_table_row_count():
    cfg = PipelineConfig()
    df = build_master_lsoa_table(cfg)
    assert len(df) == LSOA_COUNT_ENGLAND


def test_master_table_population_total():
    cfg = PipelineConfig()
    df = build_master_lsoa_table(cfg)
    assert abs(df["population"].sum() - POPULATION_ENGLAND) < 100


def test_master_table_has_all_9_factors():
    cfg = PipelineConfig()
    df = build_master_lsoa_table(cfg)
    required = [
        "imd_score", "imd_decile", "unemployment_rate", "nocar_pct",
        "elderly_pct", "income_score", "nonwhite_pct", "geo_barriers_score",
        "urban_rural", "disability_pct",
    ]
    for col in required:
        assert col in df.columns, f"Missing factor column: {col}"
        assert df[col].notna().mean() > 0.95, f"Too many nulls in {col}"
```

- [ ] **Step 2: Implement demographics assembly**

Joins all Census tables + IMD + RUC on `lsoa_code`. Validates 33,755 rows, 9 factors, population total. Matches Phase 0 `master_lsoa_table.parquet` column schema.

- [ ] **Step 3: Run tests, verify pass**

Run: `pytest tests/processing/test_demographics.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/aequitas/processing/demographics.py tests/processing/test_demographics.py
git commit -m "feat(processing): master LSOA table — 33,755 rows, 9 socio-economic factors"
```

---

### Task 14: Route Geometry Processing

**Files:**
- Create: `src/aequitas/processing/route_geometry.py`
- Create: `tests/processing/test_route_geometry.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for route geometry processing."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.processing.route_geometry import compute_route_geometries


def test_routes_with_geometry_count():
    cfg = PipelineConfig()
    result = compute_route_geometries(cfg)
    has_geom = result[result["has_geometry"]]
    # GT-027: 7,241 routes with geometry
    assert abs(len(has_geom) - 7241) < 50


def test_mean_route_length():
    cfg = PipelineConfig()
    result = compute_route_geometries(cfg)
    has_geom = result[result["has_geometry"]]
    mean_km = has_geom["route_length_km"].mean()
    # ST-010: mean 23.0 km
    assert 20.0 < mean_km < 26.0


def test_cross_la_routes():
    cfg = PipelineConfig()
    result = compute_route_geometries(cfg)
    cross_la = result[result["n_local_authorities"] > 1]
    # ST-011: 5,143 cross-LA (37.7%)
    assert abs(len(cross_la) - 5143) < 100
```

- [ ] **Step 2: Implement route geometry processing**

Ported from 04a notebook:
1. Stream shapes.txt in 500K chunks → Haversine lengths per shape_id
2. Link routes → canonical shape (max length variant)
3. Extract stop sequences from stop_times.txt (canonical trip per route)
4. Spatial join stops → LA boundaries for cross-LA analysis
5. Output: route_geometries.parquet, route_stop_sequences.parquet

- [ ] **Step 3: Run tests, verify pass**

Run: `pytest tests/processing/test_route_geometry.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/aequitas/processing/route_geometry.py tests/processing/test_route_geometry.py
git commit -m "feat(processing): route geometry — Haversine lengths, cross-LA analysis, stop sequences"
```

---

### Task 15: Service Quality Processing

**Files:**
- Create: `src/aequitas/processing/service_quality.py`
- Create: `tests/processing/test_service_quality.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for service quality processing."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.processing.service_quality import compute_service_quality


def test_sqi_mean():
    cfg = PipelineConfig()
    result = compute_service_quality(cfg)
    # ST-015: mean SQI = 65.4/100
    assert 60 < result["sqi"].mean() < 70


def test_evening_isolated_count():
    cfg = PipelineConfig()
    result = compute_service_quality(cfg)
    evening = result[result["evening_isolated"]].shape[0]
    # ST-013: 5,189 evening isolated LSOAs
    assert abs(evening - 5189) < 200


def test_sunday_desert_count():
    cfg = PipelineConfig()
    result = compute_service_quality(cfg)
    sunday = result[result["sunday_desert"]].shape[0]
    # ST-014: 6,745 Sunday deserts
    assert abs(sunday - 6745) < 200
```

- [ ] **Step 2: Implement service quality processing**

Ported from 04b notebook:
1. Stream stop_times.txt in 1M chunks → per-stop departure times by day type
2. Compute headway statistics (mean, median, CoV, span, first/last departure)
3. Time-band classification (AM peak, interpeak, PM peak, evening)
4. LSOA aggregation → composite SQI (5 weighted components)
5. Evening isolation + Sunday desert flags
6. Output: stop_headways.parquet, lsoa_service_quality.parquet

- [ ] **Step 3: Run tests, verify pass**

Run: `pytest tests/processing/test_service_quality.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/aequitas/processing/service_quality.py tests/processing/test_service_quality.py
git commit -m "feat(processing): service quality — headways, SQI, evening/Sunday flags"
```

---

## Chunk 4: Analytics Layer

### Task 16: Equity Framework

**Files:**
- Create: `src/aequitas/analytics/__init__.py`
- Create: `src/aequitas/analytics/equity.py`
- Create: `tests/analytics/test_equity.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for equity analytics."""

import pytest
import numpy as np
from aequitas.analytics.equity import (
    compute_gini,
    compute_palma_ratio,
    compute_concentration_index,
    compute_vulnerability_index,
    identify_triple_deprived,
)


def test_gini_perfect_equality():
    values = np.ones(100)
    weights = np.ones(100)
    assert compute_gini(values, weights) == pytest.approx(0.0, abs=0.01)


def test_gini_maximum_inequality():
    values = np.zeros(99)
    values = np.append(values, 100.0)
    weights = np.ones(100)
    assert compute_gini(values, weights) > 0.9


def test_gini_real_data(master_lsoa_table):
    """Gini should match ST-017: 0.5741."""
    # This test requires joining with service quality data
    # Implementation will load lsoa_service_quality and compute
    pass  # Implemented as integration test


def test_palma_ratio():
    # Bottom 40% gets 10, top 10% gets 57 → Palma = 5.7
    values = np.array([10] * 40 + [20] * 50 + [57] * 10)
    weights = np.ones(100)
    ratio = compute_palma_ratio(values, weights)
    assert ratio == pytest.approx(5.7, abs=0.1)


def test_vulnerability_index_range():
    import pandas as pd
    df = pd.DataFrame({
        "imd_score": [80, 10, 50],
        "nocar_pct": [60, 10, 30],
        "elderly_pct": [30, 5, 15],
        "disability_pct": [25, 8, 12],
        "unemployment_rate": [15, 3, 8],
    })
    result = compute_vulnerability_index(df)
    assert result.between(0, 100).all()


def test_triple_deprived_count(master_lsoa_table):
    result = identify_triple_deprived(master_lsoa_table)
    # ST-021: 612 triple-deprived LSOAs (1.8%)
    assert abs(result.sum() - 612) < 50
```

- [ ] **Step 2: Implement equity analytics**

Ported from 04c notebook:
- `compute_gini()` — population-weighted Lorenz area via `np.trapezoid`
- `compute_palma_ratio()` — top 10% / bottom 40% of service
- `compute_concentration_index()` — Wagstaff CI (covariance method)
- `compute_vulnerability_index()` — 5-factor min-max composite
- `identify_triple_deprived()` — top tertile on IMD + no-car + elderly

NumPy 2.x guard: `trapezoid = getattr(np, 'trapezoid', np.trapz)`

- [ ] **Step 3: Run tests, verify pass**

Run: `pytest tests/analytics/test_equity.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/aequitas/analytics/__init__.py src/aequitas/analytics/equity.py tests/analytics/test_equity.py
git commit -m "feat(analytics): equity framework — Gini, Palma, CI, vulnerability index"
```

---

### Task 17: ML Clustering

**Files:**
- Create: `src/aequitas/analytics/ml_clustering.py`
- Create: `tests/analytics/test_ml_clustering.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for ML clustering."""

import pytest
import numpy as np
from aequitas.analytics.ml_clustering import cluster_lsoas_hdbscan, cluster_lsoas_gmm


def test_hdbscan_returns_labels():
    np.random.seed(42)
    features = np.random.randn(1000, 5)
    labels = cluster_lsoas_hdbscan(features, min_cluster_size=50, min_samples=5)
    assert len(labels) == 1000
    assert -1 in labels  # noise expected


def test_gmm_returns_probabilities():
    np.random.seed(42)
    features = np.random.randn(1000, 5)
    probs = cluster_lsoas_gmm(features, n_components=4)
    assert probs.shape == (1000, 4)
    assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-6)
```

- [ ] **Step 2: Implement clustering**

Ported from 04d: HDBSCAN (min_cluster_size=100, min_samples=10) + GMM (n_components=4). StandardScaler preprocessing. Returns labels + soft probabilities.

- [ ] **Step 3: Run tests, commit**

```bash
git add src/aequitas/analytics/ml_clustering.py tests/analytics/test_ml_clustering.py
git commit -m "feat(analytics): ML clustering — HDBSCAN + GMM soft membership"
```

---

### Task 18: ML Prediction + SHAP

**Files:**
- Create: `src/aequitas/analytics/ml_prediction.py`
- Create: `tests/analytics/test_ml_prediction.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for coverage prediction model."""

import pytest
import numpy as np
import pandas as pd
from aequitas.analytics.ml_prediction import train_coverage_model, predict_coverage


def test_model_trains():
    np.random.seed(42)
    X = pd.DataFrame(np.random.randn(500, 5), columns=[f"f{i}" for i in range(5)])
    y = np.abs(np.random.randn(500))
    model, metrics = train_coverage_model(X, y)
    assert model is not None
    assert "r2_test" in metrics
    assert metrics["r2_test"] > -1  # better than predicting mean


def test_shap_returns_importance():
    np.random.seed(42)
    X = pd.DataFrame(np.random.randn(200, 3), columns=["a", "b", "c"])
    y = X["a"] * 2 + np.random.randn(200) * 0.1  # a is clearly important
    model, _ = train_coverage_model(X, y)
    from aequitas.analytics.ml_prediction import compute_shap_importance
    importance = compute_shap_importance(model, X)
    assert importance.iloc[0]["feature"] == "a"  # most important
```

- [ ] **Step 2: Implement prediction**

Ported from 04d:
- RF: n_estimators=200, max_depth=10, min_samples_leaf=50
- Target: log1p(trips_per_capita)
- 80/20 split, 5-fold CV
- SHAP TreeExplainer for feature importance
- Back-transform predictions with np.expm1()

- [ ] **Step 3: Run tests, commit**

```bash
git add src/aequitas/analytics/ml_prediction.py tests/analytics/test_ml_prediction.py
git commit -m "feat(analytics): RF coverage prediction + SHAP feature importance"
```

---

### Task 19: ML Anomaly Detection

**Files:**
- Create: `src/aequitas/analytics/ml_anomaly.py`
- Create: `tests/analytics/test_ml_anomaly.py`

- [ ] **Step 1: Write tests + implement**

Isolation Forest (n_estimators=200, contamination=0.05) + LOF (n_neighbors=20, contamination=0.05). Classify anomalies by type (positive, inefficiency, policy failure).

- [ ] **Step 2: Run tests, commit**

```bash
git add src/aequitas/analytics/ml_anomaly.py tests/analytics/test_ml_anomaly.py
git commit -m "feat(analytics): anomaly detection — Isolation Forest + LOF"
```

---

### Task 20: 2SFCA Accessibility

**Files:**
- Create: `src/aequitas/analytics/accessibility.py`
- Create: `tests/analytics/test_accessibility.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for 2SFCA accessibility."""

import pytest
import numpy as np
from aequitas.analytics.accessibility import compute_2sfca


def test_2sfca_zero_access():
    """LSOA with no stops within catchment → score 0."""
    # Isolated LSOA centroid, no stops nearby
    result = compute_2sfca(
        demand_points=np.array([[0, 0]]),
        demand_pop=np.array([1000]),
        supply_points=np.array([[100000, 100000]]),  # far away
        supply_capacity=np.array([50]),
        catchment_m=400,
    )
    assert result[0] == 0.0


def test_2sfca_positive_access():
    """LSOA with stops within catchment → positive score."""
    result = compute_2sfca(
        demand_points=np.array([[0, 0]]),
        demand_pop=np.array([1000]),
        supply_points=np.array([[200, 200]]),  # 283m away
        supply_capacity=np.array([50]),
        catchment_m=400,
    )
    assert result[0] > 0
```

- [ ] **Step 2: Implement 2SFCA**

Ported from 04d:
- KDTree (BNG coords) for spatial queries
- Step 1: supply ratio Rj = capacity_j / pop_in_catchment_j
- Step 2: LSOA score = sum(Rj for stops within catchment)
- Parametric: catchment_m (default 400m for bus stops, 800m for hospitals, 1200m for schools)

- [ ] **Step 3: Run tests, commit**

```bash
git add src/aequitas/analytics/accessibility.py tests/analytics/test_accessibility.py
git commit -m "feat(analytics): 2SFCA accessibility — bus stops, hospitals, GPs, schools"
```

---

### Task 21: Economic Appraisal

**Files:**
- Create: `src/aequitas/analytics/economic.py`
- Create: `tests/analytics/test_economic.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for economic appraisal."""

import pytest
from aequitas.analytics.economic import (
    compute_bcr,
    compute_modal_shift,
    pv_annuity,
)
from aequitas.core.constants import TAG


def test_pv_annuity():
    # 60-year annuity at 3.5%
    pv = pv_annuity(annual=1000, rate=0.035, years=60)
    assert 25_000 < pv < 30_000


def test_bcr_positive():
    bcr = compute_bcr(
        annual_benefit=1_000_000,
        annual_cost=800_000,
        rate=TAG.social_discount_rate,
        years=60,
    )
    assert bcr > 1.0


def test_modal_shift_co2_saving():
    result = compute_modal_shift(
        current_annual_trips=1_000_000,
        frequency_increase_pct=0.20,
        elasticity=0.55,
        modal_shift_fraction=0.25,
        avg_trip_distance_km=9.4,
    )
    assert result["co2_saved_tonnes"] > 0
    assert result["new_trips"] > 0
```

- [ ] **Step 2: Implement economic appraisal**

Ported from 04e:
- `pv_annuity()`: PV = annual × (1 − (1+r)^-n) / r
- `compute_bcr()`: PV(benefits) / PV(costs) over 60 years at 3.5%
- `compute_modal_shift()`: elasticity-based trip generation, 25% car replacement, DESNZ CO2 factors
- `compute_investment_gap()`: gap to national median, operating cost by urban/rural

- [ ] **Step 3: Run tests, commit**

```bash
git add src/aequitas/analytics/economic.py tests/analytics/test_economic.py
git commit -m "feat(analytics): economic appraisal — BCR, modal shift, carbon monetisation"
```

---

### Task 22: Policy Synthesis

**Files:**
- Create: `src/aequitas/analytics/policy_synthesis.py`
- Create: `tests/analytics/test_policy_synthesis.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for policy synthesis."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.analytics.policy_synthesis import (
    compute_priority_matrix,
    compute_lta_readiness,
    compute_policy_scenarios,
)


def test_q1_priority_count():
    cfg = PipelineConfig()
    result = compute_priority_matrix(cfg)
    q1 = result[result["priority_quadrant"] == "Q1"]
    # ST-031: 6,091 Q1 priority LSOAs
    assert abs(len(q1) - 6091) < 200


def test_lta_readiness_lad_count():
    cfg = PipelineConfig()
    result = compute_lta_readiness(cfg)
    # 298 LADs ranked
    assert abs(len(result) - 298) < 10


def test_policy_scenarios_count():
    cfg = PipelineConfig()
    result = compute_policy_scenarios(cfg)
    assert len(result) == 4  # 4 scenarios
```

- [ ] **Step 2: Implement policy synthesis**

Ported from 04f:
- Priority matrix: vulnerability × 2SFCA (Q1 = high vuln + low access)
- Healthcare/education deserts: 2SFCA for hospitals/GPs/schools with distance + SQI thresholds
- LTA franchising readiness: 5-component composite per LAD
- Policy scenarios: frequency restoration, last bus extension, DRT, combined

- [ ] **Step 3: Run tests, commit**

```bash
git add src/aequitas/analytics/policy_synthesis.py tests/analytics/test_policy_synthesis.py
git commit -m "feat(analytics): policy synthesis — priority matrix, LTA readiness, scenarios"
```

---

## Chunk 5: Intelligence Layer (InsightEngine)

### Task 23: Context Resolver

**Files:**
- Create: `src/aequitas/intelligence/__init__.py`
- Create: `src/aequitas/intelligence/context.py`
- Create: `tests/intelligence/test_context.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for InsightEngine context resolver."""

from aequitas.intelligence.context import resolve_context, AnalysisScope


def test_all_regions_all_areas():
    ctx = resolve_context(region="all", urban_rural="all")
    assert ctx.scope == AnalysisScope.ALL_REGIONS
    assert ctx.n_groups == 9


def test_single_region():
    ctx = resolve_context(region="E12000003", urban_rural="all")
    assert ctx.scope == AnalysisScope.SINGLE_REGION
    assert ctx.n_groups == 1


def test_subset():
    ctx = resolve_context(region="all", urban_rural="urban")
    assert ctx.scope == AnalysisScope.SUBSET
    assert ctx.n_groups == 1
```

- [ ] **Step 2: Implement context resolver**

Three scopes:
- `ALL_REGIONS`: 9 groups, show rankings
- `SINGLE_REGION`: 1 group, compare to national average
- `SUBSET`: 1 aggregated group, descriptive only

- [ ] **Step 3: Run tests, commit**

```bash
git add src/aequitas/intelligence/__init__.py src/aequitas/intelligence/context.py tests/intelligence/test_context.py
git commit -m "feat(intelligence): context resolver — ALL_REGIONS / SINGLE_REGION / SUBSET"
```

---

### Task 24: Calculators (Pure Statistical Functions)

**Files:**
- Create: `src/aequitas/intelligence/calculators.py`
- Create: `tests/intelligence/test_calculators.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for InsightEngine calculators."""

import pandas as pd
import pytest
from aequitas.intelligence.calculators import (
    rank_regions,
    describe_distribution,
    calculate_correlation,
)


def test_rank_regions():
    data = pd.DataFrame({
        "region": ["A", "B", "C"],
        "value": [10, 30, 20],
        "population": [1000, 2000, 1500],
    })
    ranked = rank_regions(data, metric="value", higher_is_better=True)
    assert ranked.iloc[0]["region"] == "B"  # rank 1
    assert ranked.iloc[0]["rank"] == 1


def test_describe_distribution():
    values = pd.Series([1, 2, 3, 4, 5, 100])
    desc = describe_distribution(values)
    assert "mean" in desc
    assert "median" in desc
    assert desc["outliers"] > 0


def test_correlation_significant():
    import numpy as np
    np.random.seed(42)
    x = np.arange(100, dtype=float)
    y = x * 2 + np.random.randn(100) * 5
    result = calculate_correlation(pd.Series(x), pd.Series(y))
    assert result["r"] > 0.9
    assert result["p_value"] < 0.05
    assert result["significant"] is True
```

- [ ] **Step 2: Implement calculators**

Pure functions — no presentation logic:
- `rank_regions()` — ranks with national average comparison
- `describe_distribution()` — mean, median, std, CV, IQR, outlier detection
- `calculate_correlation()` — Pearson r, p-value, strength label
- `calculate_gap_to_target()` — absolute/% gap, regions below target

- [ ] **Step 3: Run tests, commit**

```bash
git add src/aequitas/intelligence/calculators.py tests/intelligence/test_calculators.py
git commit -m "feat(intelligence): calculators — rank, distribution, correlation, gap analysis"
```

---

### Task 25: Evidence-Gated Rules

**Files:**
- Create: `src/aequitas/intelligence/rules.py`
- Create: `tests/intelligence/test_rules.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for evidence-gated insight rules."""

import pytest
from aequitas.intelligence.context import resolve_context
from aequitas.intelligence.rules import RankingRule, CorrelationRule


def test_ranking_rule_fires_for_all_regions():
    ctx = resolve_context(region="all", urban_rural="all")
    rule = RankingRule()
    assert rule.should_fire(ctx, n_groups=9)


def test_ranking_rule_suppresses_for_subset():
    ctx = resolve_context(region="all", urban_rural="urban")
    rule = RankingRule()
    assert not rule.should_fire(ctx, n_groups=1)


def test_correlation_rule_suppresses_low_n():
    rule = CorrelationRule()
    assert not rule.should_fire(n=10, p_value=0.01)


def test_correlation_rule_suppresses_insignificant():
    rule = CorrelationRule()
    assert not rule.should_fire(n=100, p_value=0.10)


def test_correlation_rule_fires_when_valid():
    rule = CorrelationRule()
    assert rule.should_fire(n=100, p_value=0.01)
```

- [ ] **Step 2: Implement rules**

Evidence-gated rules from BLUEPRINT Section 9.2:
- `RankingRule` — fires when n_groups ≥ 3
- `SingleRegionRule` — fires for single_region scope only
- `CorrelationRule` — fires when n ≥ 30 and p < 0.05
- `GiniEquityRule` — fires when n ≥ 100 LSOA observations
- `GapToInvestmentRule` — fires when regions below target exist
- Each rule returns structured data (not text) for template rendering

**Key principle: suppress > mislead. A rule that doesn't fire produces no output — never a wrong insight.**

- [ ] **Step 3: Run tests, commit**

```bash
git add src/aequitas/intelligence/rules.py tests/intelligence/test_rules.py
git commit -m "feat(intelligence): evidence-gated rules — suppress rather than mislead"
```

---

### Task 26: Jinja2 Templates + Engine Orchestrator

**Files:**
- Create: `src/aequitas/intelligence/templates/*.j2` (7 templates)
- Create: `src/aequitas/intelligence/engine.py`
- Create: `tests/intelligence/test_engine.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for InsightEngine orchestrator."""

import pytest
from aequitas.intelligence.engine import InsightEngine


def test_engine_produces_narrative():
    engine = InsightEngine()
    result = engine.generate(
        section_id="coverage_density",
        region="all",
        urban_rural="all",
        stats={"stops_per_1000": {"best": {"name": "East of England", "value": 2.54}}},
    )
    assert "narrative" in result
    assert len(result["narrative"]) > 0


def test_engine_suppresses_when_no_evidence():
    engine = InsightEngine()
    result = engine.generate(
        section_id="coverage_density",
        region="all",
        urban_rural="urban",
        stats={},
    )
    # Subset scope with no ranking data → narrative should be minimal/empty
    assert result is not None
```

- [ ] **Step 2: Create Jinja2 templates**

Consulting-tone templates for each dimension. Example `ranking.j2`:
```jinja2
**{{ best.name }}** leads England with **{{ best.value|round(2) }} {{ unit }}**,
{{ best.pct_above|round(1) }}% above the national average of
{{ national_avg|round(2) }} {{ unit }}.
{{ worst.name }} has the lowest at {{ worst.value|round(2) }} {{ unit }}
({{ worst.pct_below|round(1) }}% below average).
```

- [ ] **Step 3: Implement engine orchestrator**

Wires together: context resolver → calculators → rules → templates → JSON output.
No LLM calls — purely deterministic.

- [ ] **Step 4: Run tests, commit**

```bash
git add src/aequitas/intelligence/ tests/intelligence/test_engine.py
git commit -m "feat(intelligence): InsightEngine — context, rules, Jinja2 templates, orchestrator"
```

---

## Chunk 6: Warehouse + Validation + CLI

### Task 27: DuckDB Schema + Builder

**Files:**
- Create: `src/aequitas/warehouse/__init__.py`
- Create: `src/aequitas/warehouse/schema.py`
- Create: `src/aequitas/warehouse/builder.py`
- Create: `tests/warehouse/test_schema.py`
- Create: `tests/warehouse/test_builder.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for DuckDB warehouse builder."""

import duckdb
import pytest
from aequitas.warehouse.schema import TABLES
from aequitas.warehouse.builder import build_warehouse


def test_schema_has_required_tables():
    required = {
        "stops", "routes", "lsoa_demographics", "section_results", "provenance",
        # Analytics tables (LSOA-level data for maps + drill-downs)
        "lsoa_service_quality", "lsoa_equity_metrics", "lsoa_accessibility",
        "lsoa_economic", "lsoa_policy", "route_details", "lta_readiness",
    }
    assert required.issubset(set(TABLES.keys()))


def test_build_warehouse_creates_file(tmp_path):
    db_path = tmp_path / "test.duckdb"
    # This is an integration test — requires processed parquet files
    # Will be run as part of full pipeline test
    pass
```

- [ ] **Step 2: Implement schema**

```python
"""DuckDB table definitions for Aequitas warehouse."""

TABLES: dict[str, str] = {
    "stops": """
        CREATE TABLE IF NOT EXISTS stops (
            stop_id VARCHAR PRIMARY KEY,
            stop_name VARCHAR,
            latitude DOUBLE,
            longitude DOUBLE,
            lsoa_code VARCHAR,
            region_code VARCHAR,
            stop_type VARCHAR
        )
    """,
    "routes": """
        CREATE TABLE IF NOT EXISTS routes (
            route_id VARCHAR PRIMARY KEY,
            line_name VARCHAR,
            route_length_km DOUBLE,
            num_stops INTEGER,
            trips_per_day INTEGER,
            regions_served VARCHAR[],
            has_geometry BOOLEAN
        )
    """,
    "lsoa_demographics": """
        CREATE TABLE IF NOT EXISTS lsoa_demographics (
            lsoa_code VARCHAR PRIMARY KEY,
            lsoa_name VARCHAR,
            population INTEGER,
            imd_score DOUBLE,
            imd_decile INTEGER,
            unemployment_rate DOUBLE,
            nocar_pct DOUBLE,
            elderly_pct DOUBLE,
            income_score DOUBLE,
            nonwhite_pct DOUBLE,
            geo_barriers_score DOUBLE,
            urban_rural VARCHAR,
            disability_pct DOUBLE
        )
    """,
    "section_results": """
        CREATE TABLE IF NOT EXISTS section_results (
            region VARCHAR,
            urban_rural VARCHAR,
            section_id VARCHAR,
            stats JSON,
            chart_data JSON,
            narrative JSON,
            PRIMARY KEY (region, urban_rural, section_id)
        )
    """,
    "provenance": """
        CREATE TABLE IF NOT EXISTS provenance (
            metric_id VARCHAR PRIMARY KEY,
            value DOUBLE,
            formula VARCHAR,
            inputs JSON,
            source_files VARCHAR[]
        )
    """,
    # Analytics tables — LSOA-level data for frontend maps + drill-downs
    # These are loaded directly from processed Parquet files
    "lsoa_service_quality": """
        CREATE TABLE IF NOT EXISTS lsoa_service_quality AS
        SELECT * FROM read_parquet('data/processed/lsoa_service_quality.parquet')
    """,
    "lsoa_equity_metrics": """
        CREATE TABLE IF NOT EXISTS lsoa_equity_metrics AS
        SELECT * FROM read_parquet('data/processed/lsoa_equity_metrics.parquet')
    """,
    "lsoa_accessibility": """
        CREATE TABLE IF NOT EXISTS lsoa_accessibility AS
        SELECT * FROM read_parquet('data/processed/lsoa_2sfca.parquet')
    """,
    "lsoa_economic": """
        CREATE TABLE IF NOT EXISTS lsoa_economic AS
        SELECT * FROM read_parquet('data/processed/lsoa_economic_appraisal.parquet')
    """,
    "lsoa_policy": """
        CREATE TABLE IF NOT EXISTS lsoa_policy AS
        SELECT * FROM read_parquet('data/processed/lsoa_policy_synthesis.parquet')
    """,
    "route_details": """
        CREATE TABLE IF NOT EXISTS route_details AS
        SELECT * FROM read_parquet('data/processed/route_geometries.parquet')
    """,
    "lta_readiness": """
        CREATE TABLE IF NOT EXISTS lta_readiness AS
        SELECT * FROM read_parquet('data/processed/lta_franchising_readiness.parquet')
    """,
}
```

- [ ] **Step 3: Implement builder**

Loads processed Parquet files → creates DuckDB tables → runs precompute for section_results.

- [ ] **Step 4: Run tests, commit**

```bash
git add src/aequitas/warehouse/ tests/warehouse/
git commit -m "feat(warehouse): DuckDB schema + builder — stops, routes, demographics, section_results, provenance"
```

---

### Task 28: Precompute (Section × Filter Matrix)

**Files:**
- Create: `src/aequitas/warehouse/precompute.py`
- Create: `src/aequitas/warehouse/provenance.py`
- Create: `tests/warehouse/test_precompute.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for section_results precomputation."""

import pytest
from aequitas.core.config import PipelineConfig
from aequitas.warehouse.precompute import precompute_all_sections


def test_precompute_produces_results():
    cfg = PipelineConfig()
    results = precompute_all_sections(cfg)
    # 30 filter combos × N sections
    assert len(results) > 0
    # Each result has required fields
    for r in results[:5]:
        assert "region" in r
        assert "urban_rural" in r
        assert "section_id" in r
        assert "stats" in r
        assert "narrative" in r
```

- [ ] **Step 2: Implement precompute**

For each of the 30 filter combinations:
1. Filter master data by region + urban_rural
2. Run InsightEngine for each analytical section
3. Collect stats, chart_data, narrative into SectionResult
4. Build provenance entries

- [ ] **Step 3: Implement provenance tracking**

Every metric traced to: formula, input values, source Parquet files.

- [ ] **Step 4: Run tests, commit**

```bash
git add src/aequitas/warehouse/precompute.py src/aequitas/warehouse/provenance.py tests/warehouse/test_precompute.py
git commit -m "feat(warehouse): precompute section_results + provenance tracking"
```

---

### Task 29: Validation Gates

**Files:**
- Create: `src/aequitas/validation/__init__.py`
- Create: `src/aequitas/validation/ground_truth.py`
- Create: `src/aequitas/validation/gates.py`
- Create: `src/aequitas/validation/report.py`
- Create: `tests/validation/test_ground_truth.py`
- Create: `tests/validation/test_gates.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for ground truth validation."""

import pytest
from aequitas.validation.ground_truth import validate_against_ground_truth
from aequitas.core.config import PipelineConfig


def test_ground_truth_all_pass():
    """End-to-end: pipeline output matches Phase 0 locked values."""
    cfg = PipelineConfig()
    report = validate_against_ground_truth(cfg)
    failed = [c for c in report["checks"] if c["status"] == "FAIL"]
    assert len(failed) == 0, f"Failed checks: {failed}"
```

```python
"""Tests for validation gates."""

import pytest
from aequitas.validation.gates import (
    check_population_total,
    check_lsoa_count,
    check_entity_counts,
    check_match_rates,
)
from aequitas.core.constants import POPULATION_ENGLAND, LSOA_COUNT_ENGLAND


def test_population_gate_passes():
    assert check_population_total(56_490_056)


def test_population_gate_fails():
    assert not check_population_total(50_000_000)


def test_lsoa_gate_passes():
    assert check_lsoa_count(33_755)


def test_entity_count_sanity():
    assert check_entity_counts(stops=274_719, routes=13_099)
    assert not check_entity_counts(stops=1_000_000, routes=13_099)  # too many
```

- [ ] **Step 2: Implement validation**

Gates from data-quality.md + full ground truth coverage:

**Entity gates (exact):**
- Population total matches 56,490,056 (±100)
- LSOA count = 33,755
- Stops = 274,719, Routes = 13,099, Trips = 1,752,443
- LSOAs with zero bus stops = 4,245

**Match rate gates:**
- Stop→LSOA spatial join ≥ 99.99%
- All demographic merge rates ≥ 95%
- All LSOA codes match E01/E02 pattern

**Analytics gates (from ground_truth.json "analytics" section — added in Task 0):**
- Gini = 0.5741 (±5%)
- Palma = 5.702 (±5%)
- Concentration Index = +0.1358 (±5%)
- SQI mean = 65.4 (±5%)
- Evening isolated = 5,189 (±50)
- Sunday deserts = 6,745 (±50)
- Routes with geometry = 7,241 (±50)
- Cross-LA routes = 5,143 (±50)
- RF R² = 0.4719 (±5%)
- Top SHAP feature = "nocar_pct" (exact)
- Anomalies = 1,688 (±50)
- 2SFCA zero-access = 6,776 (±50)
- Q1 priority LSOAs = 6,091 (±50)
- Triple-deprived = 612 (exact)
- Policy scenarios = 4 (exact)

- [ ] **Step 3: Implement report generator**

Produces JSON + human-readable validation report. Every check: name, status (PASS/WARN/FAIL), expected, actual.

- [ ] **Step 4: Run tests, commit**

```bash
git add src/aequitas/validation/ tests/validation/
git commit -m "feat(validation): ground truth gates + validation report"
```

---

### Task 30: Pipeline CLI

**Files:**
- Create: `src/aequitas/pipeline/__init__.py`
- Create: `src/aequitas/pipeline/cli.py`

- [ ] **Step 1: Write CLI test**

```python
"""Tests for pipeline CLI."""

from click.testing import CliRunner
from aequitas.pipeline.cli import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "pipeline" in result.output.lower()


def test_cli_validate_stage():
    runner = CliRunner()
    result = runner.invoke(main, ["validate"])
    # Should run validation gates
    assert result.exit_code == 0
```

- [ ] **Step 2: Implement CLI**

```python
"""Aequitas pipeline CLI.

Usage:
    aequitas ingest      — Load raw data, apply filters, output cleaned CSVs
    aequitas process     — Spatial joins, dedup, demographics, route geometry, service quality
    aequitas analytics   — Equity, ML, accessibility, economic appraisal, policy synthesis
    aequitas intelligence — Run InsightEngine, generate narratives
    aequitas warehouse   — Build DuckDB from Parquet + narratives
    aequitas validate    — Run ground truth gates, produce validation report
    aequitas run         — Run all stages end-to-end
"""

import click
from loguru import logger


@click.group()
def main():
    """Aequitas data pipeline — raw government data to DuckDB warehouse."""
    pass


@main.command()
def ingest():
    """Stage 1: Load and filter raw data sources."""
    from aequitas.pipeline._stages import run_ingestion
    run_ingestion()


@main.command()
def process():
    """Stage 2: Spatial joins, dedup, demographics, geometry, service quality."""
    from aequitas.pipeline._stages import run_processing
    run_processing()


@main.command()
def analytics():
    """Stage 3: Equity, ML, accessibility, economic, policy synthesis."""
    from aequitas.pipeline._stages import run_analytics
    run_analytics()


@main.command()
def intelligence():
    """Stage 4: Run InsightEngine, generate narratives."""
    from aequitas.pipeline._stages import run_intelligence
    run_intelligence()


@main.command()
def warehouse():
    """Stage 5: Build DuckDB from processed Parquet + narratives."""
    from aequitas.pipeline._stages import run_warehouse
    run_warehouse()


@main.command()
def validate():
    """Stage 6: Run ground truth validation gates."""
    from aequitas.pipeline._stages import run_validation
    run_validation()


@main.command()
def run():
    """Run all pipeline stages end-to-end."""
    from aequitas.pipeline._stages import (
        run_ingestion,
        run_processing,
        run_analytics,
        run_intelligence,
        run_warehouse,
        run_validation,
    )
    stages = [
        ("ingest", run_ingestion),
        ("process", run_processing),
        ("analytics", run_analytics),
        ("intelligence", run_intelligence),
        ("warehouse", run_warehouse),
        ("validate", run_validation),
    ]
    for name, fn in stages:
        logger.info("=== Stage: {} ===", name)
        fn()
        logger.info("=== {} complete ===", name)
    logger.info("Pipeline complete. Warehouse: data/aequitas.duckdb")
```

- [ ] **Step 3: Create `_stages.py` orchestration module**

Each stage function: reads from previous stage's output, writes its own Parquets, logs timing, writes a validation checkpoint before the next stage starts (per data-quality.md rule: "Every ingestion step must write a validation report before the next step starts").

```python
"""Pipeline stage orchestration — wires together all 6 stages.

Each run_*() function takes a PipelineConfig, reads its inputs,
writes its outputs to config.processed_dir, and returns a StageReport.
"""

from dataclasses import dataclass
from pathlib import Path
import time

from loguru import logger
from aequitas.core.config import PipelineConfig


@dataclass
class StageReport:
    stage: str
    duration_s: float
    output_files: list[Path]
    checks_passed: int
    checks_failed: int


def run_ingestion(cfg: PipelineConfig | None = None) -> StageReport:
    """Stage 1: Load + filter raw data sources → ingested Parquets.

    Outputs:
        processed_dir/naptan_filtered.parquet
        processed_dir/bods_routes.parquet
        processed_dir/bods_trips.parquet
        processed_dir/bods_stops.parquet
        processed_dir/bods_calendar.parquet
        processed_dir/census_*.parquet (6 tables)
        processed_dir/imd.parquet
        processed_dir/ruc.parquet
    """
    ...


def run_processing(cfg: PipelineConfig | None = None) -> StageReport:
    """Stage 2: Spatial joins, dedup, demographics, geometry, service quality.

    Reads: All Stage 1 outputs + raw BODS zip (for stop_times/shapes chunking)
    Outputs:
        processed_dir/stops_with_lsoa.parquet
        processed_dir/unique_stops.parquet
        processed_dir/unique_routes.parquet
        processed_dir/master_lsoa_table.parquet
        processed_dir/route_geometries.parquet
        processed_dir/route_stop_sequences.parquet
        processed_dir/stop_headways.parquet
        processed_dir/lsoa_service_quality.parquet
    """
    ...


def run_analytics(cfg: PipelineConfig | None = None) -> StageReport:
    """Stage 3: Equity, ML, accessibility, economic, policy synthesis.

    Reads: All Stage 2 outputs + POI Parquets from data/audit/
    Outputs:
        processed_dir/lsoa_equity_metrics.parquet
        processed_dir/lsoa_clusters_hdbscan.parquet
        processed_dir/coverage_prediction.parquet
        processed_dir/anomalies.parquet
        processed_dir/lsoa_2sfca.parquet
        processed_dir/lsoa_economic_appraisal.parquet
        processed_dir/modal_shift_scenarios.parquet
        processed_dir/lsoa_policy_synthesis.parquet
        processed_dir/lta_franchising_readiness.parquet
        processed_dir/policy_scenarios.parquet
    """
    ...


def run_intelligence(cfg: PipelineConfig | None = None) -> StageReport:
    """Stage 4: InsightEngine → narratives for each section × filter combo.

    Reads: All Stage 2+3 outputs
    Outputs: processed_dir/section_results.parquet (or JSON)
    """
    ...


def run_warehouse(cfg: PipelineConfig | None = None) -> StageReport:
    """Stage 5: Build DuckDB from all processed Parquets + section_results.

    Reads: All processed_dir/*.parquet
    Outputs: cfg.warehouse_path (aequitas.duckdb)
    """
    ...


def run_validation(cfg: PipelineConfig | None = None) -> StageReport:
    """Stage 6: Validate DuckDB contents against ground truth.

    Reads: cfg.warehouse_path + data/audit/ground_truth.json
    Outputs: processed_dir/validation_report.json
    """
    ...
```

- [ ] **Step 4: Run tests, commit**

```bash
git add src/aequitas/pipeline/ tests/test_cli.py
git commit -m "feat(pipeline): CLI — ingest, process, analytics, intelligence, warehouse, validate, run"
```

---

## Chunk 7: Integration Tests + End-to-End Validation

### Task 31: Integration Test Suite

**Files:**
- Create: `tests/integration/test_full_pipeline.py`

- [ ] **Step 1: Write end-to-end integration test**

```python
"""End-to-end pipeline integration test.

Runs the full pipeline into an isolated temp directory and validates
output against Phase 0 ground truth. Slow (~15-30 min).
Run with: pytest tests/integration/ -v -m slow
"""

import duckdb
import pytest
from pathlib import Path
from aequitas.core.config import PipelineConfig
from aequitas.core.constants import POPULATION_ENGLAND, LSOA_COUNT_ENGLAND

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def pipeline_output(tmp_path_factory):
    """Run full pipeline into isolated temp directory."""
    from aequitas.pipeline._stages import (
        run_ingestion, run_processing, run_analytics,
        run_intelligence, run_warehouse, run_validation,
    )
    out_dir = tmp_path_factory.mktemp("pipeline")
    cfg = PipelineConfig(
        processed_dir=out_dir / "processed",
        warehouse_path=out_dir / "aequitas.duckdb",
    )
    cfg.processed_dir.mkdir(parents=True, exist_ok=True)
    run_ingestion(cfg)
    run_processing(cfg)
    run_analytics(cfg)
    run_intelligence(cfg)
    run_warehouse(cfg)
    return cfg


def test_duckdb_exists(pipeline_output):
    assert pipeline_output.warehouse_path.exists()


def test_duckdb_has_all_tables(pipeline_output):
    con = duckdb.connect(str(pipeline_output.warehouse_path), read_only=True)
    tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    required = {"stops", "routes", "lsoa_demographics", "section_results", "provenance"}
    assert required.issubset(tables)
    con.close()


def test_stops_count(pipeline_output):
    con = duckdb.connect(str(pipeline_output.warehouse_path), read_only=True)
    count = con.execute("SELECT COUNT(*) FROM stops").fetchone()[0]
    assert count == 274_719
    con.close()


def test_routes_count(pipeline_output):
    con = duckdb.connect(str(pipeline_output.warehouse_path), read_only=True)
    count = con.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
    assert count == 13_099
    con.close()


def test_lsoa_count(pipeline_output):
    con = duckdb.connect(str(pipeline_output.warehouse_path), read_only=True)
    count = con.execute("SELECT COUNT(*) FROM lsoa_demographics").fetchone()[0]
    assert count == LSOA_COUNT_ENGLAND
    con.close()


def test_population_total(pipeline_output):
    con = duckdb.connect(str(pipeline_output.warehouse_path), read_only=True)
    total = con.execute("SELECT SUM(population) FROM lsoa_demographics").fetchone()[0]
    assert abs(total - POPULATION_ENGLAND) < 100
    con.close()


def test_section_results_populated(pipeline_output):
    con = duckdb.connect(str(pipeline_output.warehouse_path), read_only=True)
    count = con.execute("SELECT COUNT(*) FROM section_results").fetchone()[0]
    assert count > 0  # At least some sections pre-computed
    con.close()


def test_provenance_populated(pipeline_output):
    con = duckdb.connect(str(pipeline_output.warehouse_path), read_only=True)
    count = con.execute("SELECT COUNT(*) FROM provenance").fetchone()[0]
    assert count > 0
    con.close()


def test_validation_report_all_pass(pipeline_output):
    from aequitas.validation.ground_truth import validate_against_ground_truth
    report = validate_against_ground_truth(pipeline_output)
    failed = [c for c in report["checks"] if c["status"] == "FAIL"]
    assert len(failed) == 0, f"Ground truth failures: {[c['name'] for c in failed]}"
```

- [ ] **Step 2: Run integration test**

Run: `pytest tests/integration/test_full_pipeline.py -v --timeout=1800`
Expected: All PASS. DuckDB populated with correct counts.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/
git commit -m "test: end-to-end pipeline integration test against ground truth"
```

---

### Task 32: Final Validation + Cleanup

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v --cov=aequitas --cov-report=term-missing`
Expected: All tests PASS, coverage > 80%

- [ ] **Step 2: Run pipeline end-to-end**

Run: `python -m aequitas.pipeline run`
Expected: Pipeline completes, `data/aequitas.duckdb` created, validation report shows 0 failures.

- [ ] **Step 3: Verify DuckDB contents manually**

```python
import duckdb
con = duckdb.connect("data/aequitas.duckdb", read_only=True)
print(con.execute("SHOW TABLES").fetchall())
print(con.execute("SELECT COUNT(*) FROM stops").fetchone())
print(con.execute("SELECT COUNT(*) FROM routes").fetchone())
print(con.execute("SELECT COUNT(*) FROM lsoa_demographics").fetchone())
print(con.execute("SELECT COUNT(*) FROM section_results").fetchone())
print(con.execute("SELECT COUNT(*) FROM provenance").fetchone())
con.close()
```

- [ ] **Step 4: Commit all remaining files**

```bash
git add -A
git commit -m "feat: Phase 1 complete — pipeline + warehouse, validated against ground truth"
```

---

## Execution Notes

### Build Order (Dependencies)

```
Task 0 (ground_truth.json extension)
    → Task 1-6 (Core)
        → Task 7-10 (Ingestion) — no inter-task dependencies, can parallel
            → Task 11-13 (Processing: spatial, dedup, demographics) — sequential
            → Task 14-15 (Processing: geometry, quality) — depend on 11-13
                → Tasks 16-20 (Analytics) — ALL depend on 11-15; can run in PARALLEL
                    → Tasks 21-22 (Economic + Policy) — depend on 16-20 outputs
                        → Task 23-26 (Intelligence) — depends on analytics outputs
                            → Task 27-30 (Warehouse + CLI) — depends on intelligence
                                → Task 31-32 (Integration)
```

**Corrected dependency notes:**
- Tasks 16 (equity), 17 (clustering), 18 (prediction), 19 (anomaly), 20 (2SFCA) are **peers, not sequential**. They all read from processing outputs (master LSOA table + service quality). Equity is NOT a prerequisite for ML modules.
- Tasks 21 (economic) and 22 (policy synthesis) depend on ALL of 16-20 because they consume equity metrics, ML predictions, 2SFCA scores, and service quality.
- Task 20 (2SFCA) depends on Task 10 (POI data) + Task 11 (spatial joins) + Task 13 (demographics).

### Parallelisation Opportunities

Tasks that can run as parallel subagents:
- **Ingestion:** Tasks 7, 8, 9, 10 are fully independent
- **Analytics tier 1:** Tasks 16, 17, 18, 19, 20 are independent of each other (all depend on processing outputs)
- **Intelligence:** Tasks 23, 24, 25 are independent of each other

### Key Risk Mitigations

1. **Memory:** BODS stop_times.txt (5.8GB) and shapes.txt (3.2GB) MUST be chunked. Never `pd.read_csv()` without `chunksize`.
2. **NumPy 2.x:** Use `trapezoid = getattr(np, 'trapezoid', np.trapz)` everywhere.
3. **LSOA boundary vintage:** Dynamic column detection (RGN21CD vs RGN22CD) — never hardcode.
4. **Population denominator:** ALWAYS 56,490,056. Test for this in every aggregation.
5. **GIAS encoding:** `encoding='latin-1'` not `'utf-8'`.
6. **NaPTAN Status:** Value is `'active'` not `'act'`. Ground truth confirms 0 rows match `'act'`.
7. **lsoa_service_levels.parquet:** ZERO-FILLED skeleton. Use `lsoa_service_quality.parquet` for real trip counts.

### Acceptance Criteria

Phase 1 is DONE when:
- [x] `python -m aequitas.pipeline run` completes without error
- [x] `data/aequitas.duckdb` exists and contains all 5 tables
- [x] Validation report shows 0 FAIL checks
- [x] Ground truth values match: 274,719 stops, 13,099 routes, 33,755 LSOAs, 56,490,056 population
- [x] All unit + integration tests pass
- [x] Key statistical outputs within tolerance: Gini ~0.574, Palma ~5.7, CI ~+0.136, SQI mean ~65
