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
