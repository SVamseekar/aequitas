from __future__ import annotations
from pydantic import BaseModel, Field


class HeadlineStat(BaseModel):
    value: float
    label: str
    severity: str  # "high", "medium", "low"


class DimensionOverview(BaseModel):
    id: str
    name: str
    headline_stat: HeadlineStat
    summary: str
    route: str


class OverviewResponse(BaseModel):
    dimensions: list[DimensionOverview]
    built_at: str | None = None
    score: float | None = None
    score_note: str | None = None
    score_n_areas: int | None = None
    score_dropped: list[str] = Field(default_factory=list)


class SectionItem(BaseModel):
    section_id: str
    dimension: str
    stats: dict
    chart_data: dict
    narrative: str
    suppressed: bool


class SectionsResponse(BaseModel):
    dimension: str
    sections: list[SectionItem]


class LsoaResponse(BaseModel):
    rows: list[dict]
    total: int


class ProvenanceResponse(BaseModel):
    metric_id: str
    value: float
    formula: str
    inputs: dict
    source_files: list[str]
