"""Policy synthesis analytics — priority matrix, LTA readiness, scenarios.

Ported from Phase 0 notebook 04f.
Loads pre-computed Phase 0 audit Parquets and re-derives policy outputs.

Ground truth:
- 6,091 Q1 priority LSOAs (high vulnerability, low access)
- 298 LADs ranked for franchising readiness
- 4 policy scenarios (A–D)
"""

from pathlib import Path

import pandas as pd

from aequitas.core.config import PipelineConfig


_Q1_LABEL = "Q1: High vulnerability, Low access (PRIORITY)"


def compute_priority_matrix(cfg: PipelineConfig) -> pd.DataFrame:
    """Classify LSOAs into four priority quadrants: vulnerability × accessibility.

    Q1 (PRIORITY): high vulnerability + low access
    Q2: high vulnerability + high access
    Q3: low vulnerability + low access
    Q4: low vulnerability + high access

    Loads the Phase 0 policy synthesis Parquet and applies vulnerability/access
    thresholds (median split on vulnerability_index and sfca_score_norm).

    Args:
        cfg: Pipeline configuration with audit_dir path.

    Returns:
        DataFrame with LSOA-level records including 'priority_quadrant' column.
    """
    path = cfg.audit_dir / "lsoa_policy_synthesis.parquet"
    df = pd.read_parquet(path)

    if "priority_quadrant" in df.columns:
        # Use pre-computed Phase 0 quadrants
        return df

    # Recompute if column absent
    vuln_median = df["vulnerability_index"].median()
    access_median = df["sfca_score_norm"].median()

    high_vuln = df["vulnerability_index"] >= vuln_median
    high_access = df["sfca_score_norm"] >= access_median

    conditions = [
        high_vuln & ~high_access,
        high_vuln & high_access,
        ~high_vuln & ~high_access,
        ~high_vuln & high_access,
    ]
    quadrants = [
        _Q1_LABEL,
        "Q2: High vulnerability, High access",
        "Q3: Low vulnerability, Low access",
        "Q4: Low vulnerability, High access",
    ]
    df["priority_quadrant"] = pd.NA
    for cond, label in zip(conditions, quadrants):
        df.loc[cond, "priority_quadrant"] = label

    return df


def compute_lta_readiness(cfg: PipelineConfig) -> pd.DataFrame:
    """Compute LTA franchising readiness composite score per LAD.

    5-component composite per LAD: HHI (operator concentration), trip gap to median,
    deprivation score, service quality, evening isolation rate.
    Each component normalised 0–100, equally weighted.

    Args:
        cfg: Pipeline configuration with audit_dir path.

    Returns:
        DataFrame with 298 LADs including 'franchising_readiness' and 'readiness_tier'.
    """
    path = cfg.audit_dir / "lta_franchising_readiness.parquet"
    return pd.read_parquet(path)


def compute_policy_scenarios(cfg: PipelineConfig) -> pd.DataFrame:
    """Load the 4 pre-computed policy intervention scenarios.

    Scenarios:
    A: Frequency restoration — restore 30% headway reduction
    B: Last bus extension — extend evening service to 23:00
    C: DRT — demand-responsive transport for rural deserts
    D: Combined — franchise + frequency + DRT bundle

    Args:
        cfg: Pipeline configuration with audit_dir path.

    Returns:
        DataFrame with 4 scenario rows.
    """
    path = cfg.audit_dir / "policy_scenarios.parquet"
    return pd.read_parquet(path)
