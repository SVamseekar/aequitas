"""Optional analytical context for tenant-owned workspace records."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_QUERY_KEYS = frozenset(
    {
        "region",
        "urban_rural",
        "pack",
        "as_of",
        "mode",
        "view",
        "exhibit",
        "metric",
        "a",
        "b",
        "dest",
        "cutoff",
        "cells",
        "freq_pct",
        "last_bus",
        "drt_cov",
        "franchise",
        "lad",
        "rank",
        "sort",
        "cluster",
        "point",
    }
)


class SavedViewContext(BaseModel):
    """A local analytical route, never an arbitrary redirect or auth payload."""

    model_config = ConfigDict(extra="forbid")

    country: Literal["england", "ireland", "netherlands", "france"]
    page: Literal[
        "overview",
        "equity",
        "access",
        "service",
        "network",
        "correlations",
        "economy",
        "policy",
        "scenarios",
        "studio",
        "compare",
        "reach",
        "time",
        "ops",
    ] = "overview"
    query: dict[str, str] = Field(default_factory=dict)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: dict[str, str]) -> dict[str, str]:
        """Keep bounded analytical controls; reject secrets and unknown keys."""
        if not set(value).issubset(_QUERY_KEYS):
            raise ValueError("Only analytical view controls may be saved")
        if any(len(item) > 256 for item in value.values()):
            raise ValueError("Saved view controls must be at most 256 characters")
        return value
