from __future__ import annotations
from pydantic import BaseModel


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
