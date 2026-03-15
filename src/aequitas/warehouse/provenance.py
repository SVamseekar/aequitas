"""Provenance tracking — trace every warehouse metric to source data.

Every metric stored in section_results must have a ProvenanceEntry that records:
- The formula used to compute it
- The input values
- The source Parquet files

This ensures every figure on screen can be traced back to source data.
"""

from dataclasses import dataclass, field


@dataclass
class ProvenanceEntry:
    """Records how a warehouse metric was derived.

    Attributes:
        metric_id: Unique identifier (e.g. "gini_coefficient").
        value: The computed metric value.
        formula: Human-readable formula string.
        inputs: Dict of input variable names to their values.
        source_files: List of Parquet/CSV files used as inputs.
    """

    metric_id: str
    value: float
    formula: str
    inputs: dict[str, float] = field(default_factory=dict)
    source_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialise for DuckDB JSON storage."""
        return {
            "metric_id": self.metric_id,
            "value": self.value,
            "formula": self.formula,
            "inputs": self.inputs,
            "source_files": self.source_files,
        }


def build_equity_provenance(gini: float, palma: float, ci: float) -> list[ProvenanceEntry]:
    """Build provenance entries for the three equity metrics.

    Args:
        gini: Gini coefficient value.
        palma: Palma ratio value.
        ci: Concentration Index value.

    Returns:
        List of three ProvenanceEntry objects.
    """
    return [
        ProvenanceEntry(
            metric_id="gini_coefficient",
            value=gini,
            formula="1 - 2 * trapezoid(cum_service, cum_pop)",
            inputs={"gini": gini},
            source_files=["lsoa_service_quality.parquet", "master_lsoa_table.parquet"],
        ),
        ProvenanceEntry(
            metric_id="palma_ratio",
            value=palma,
            formula="mean_service_top10pct / mean_service_bottom40pct",
            inputs={"palma": palma},
            source_files=["lsoa_service_quality.parquet", "master_lsoa_table.parquet"],
        ),
        ProvenanceEntry(
            metric_id="concentration_index",
            value=ci,
            formula="2 * cov(service, fractional_rank) / mean_service",
            inputs={"ci": ci},
            source_files=["lsoa_service_quality.parquet", "imd2025_all_ranks_scores_deciles.csv"],
        ),
    ]
