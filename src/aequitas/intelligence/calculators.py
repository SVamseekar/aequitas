"""InsightEngine calculators — pure statistical functions, no presentation logic.

Functions:
- rank_regions: rank by metric with national average comparison
- describe_distribution: mean, median, std, CV, IQR, outlier count
- calculate_correlation: Pearson r, p-value, strength label
- calculate_gap_to_target: absolute/% gap, count below target
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats


def rank_regions(
    data: pd.DataFrame,
    metric: str,
    higher_is_better: bool = True,
) -> pd.DataFrame:
    """Rank regions by a metric, adding rank and comparison to national average.

    Args:
        data: DataFrame with a 'region' column and the metric column.
        metric: Column name to rank by.
        higher_is_better: True = rank 1 is the highest value.

    Returns:
        DataFrame sorted by rank ascending, with added columns:
        'rank', 'national_mean', 'vs_national_pct' (% difference from national mean).
    """
    result = data.copy()
    ascending = not higher_is_better
    result["rank"] = result[metric].rank(ascending=ascending, method="min").astype(int)
    national_mean = result[metric].mean()
    result["national_mean"] = round(national_mean, 4)
    result["vs_national_pct"] = round(
        (result[metric] - national_mean) / national_mean * 100, 2
    )
    return result.sort_values("rank").reset_index(drop=True)


@dataclass
class DistributionSummary:
    mean: float
    median: float
    std: float
    cv: float
    """Coefficient of variation (std/mean). High CV = heterogeneous."""
    iqr: float
    p10: float
    p90: float
    outliers: int
    """Count of values beyond 3× IQR from Q1/Q3 (mild outliers excluded)."""


def describe_distribution(values: pd.Series) -> DistributionSummary:
    """Compute key distributional statistics for a metric series.

    Args:
        values: Numeric pandas Series.

    Returns:
        DistributionSummary with mean, median, std, CV, IQR, p10, p90, outlier count.
    """
    q1 = float(values.quantile(0.25))
    q3 = float(values.quantile(0.75))
    iqr = q3 - q1
    lower_fence = q1 - 3 * iqr
    upper_fence = q3 + 3 * iqr
    outlier_count = int(((values < lower_fence) | (values > upper_fence)).sum())
    mean = float(values.mean())
    std = float(values.std())
    cv = float(std / mean) if mean != 0 else float("inf")

    return DistributionSummary(
        mean=round(mean, 4),
        median=round(float(values.median()), 4),
        std=round(std, 4),
        cv=round(cv, 4),
        iqr=round(iqr, 4),
        p10=round(float(values.quantile(0.10)), 4),
        p90=round(float(values.quantile(0.90)), 4),
        outliers=outlier_count,
    )


_STRENGTH_THRESHOLDS = [
    (0.9, "very strong"),
    (0.7, "strong"),
    (0.5, "moderate"),
    (0.3, "weak"),
    (0.0, "negligible"),
]


@dataclass
class CorrelationResult:
    r: float
    p_value: float
    n: int
    significant: bool
    """p_value < 0.05."""
    strength: str
    """negligible / weak / moderate / strong / very strong."""
    direction: Literal["positive", "negative", "none"]


def calculate_correlation(x: pd.Series, y: pd.Series) -> CorrelationResult:
    """Compute Pearson correlation between two numeric series.

    Args:
        x: First numeric series (same length as y).
        y: Second numeric series.

    Returns:
        CorrelationResult with r, p_value, n, significance, and strength label.
    """
    # Drop rows where either series is NaN
    mask = x.notna() & y.notna()
    xv = x[mask].values
    yv = y[mask].values
    n = int(len(xv))

    if n < 3:
        return CorrelationResult(
            r=0.0, p_value=1.0, n=n, significant=False, strength="negligible", direction="none"
        )

    r, p_value = scipy_stats.pearsonr(xv, yv)
    r = float(r)
    p_value = float(p_value)
    abs_r = abs(r)

    strength = "negligible"
    for threshold, label in _STRENGTH_THRESHOLDS:
        if abs_r >= threshold:
            strength = label
            break

    direction: Literal["positive", "negative", "none"] = (
        "positive" if r > 0.01 else "negative" if r < -0.01 else "none"
    )

    return CorrelationResult(
        r=round(r, 4),
        p_value=round(p_value, 6),
        n=n,
        significant=p_value < 0.05,
        strength=strength,
        direction=direction,
    )


@dataclass
class GapAnalysis:
    target: float
    n_below_target: int
    pct_below_target: float
    mean_gap: float
    """Mean absolute gap for units below target."""
    total_gap: float
    """Sum of absolute gaps for units below target."""


def calculate_gap_to_target(
    values: pd.Series,
    target: float,
    weights: pd.Series | None = None,
) -> GapAnalysis:
    """Calculate gap analysis: how many units are below a target, and by how much.

    Args:
        values: Metric values per LSOA/LAD.
        target: Benchmark value (e.g. national median).
        weights: Optional population weights for weighted gap calculation.

    Returns:
        GapAnalysis with count below target, pct, mean gap, total gap.
    """
    below_mask = values < target
    n_below = int(below_mask.sum())
    pct_below = round(float(n_below / len(values) * 100), 2)

    gaps = target - values[below_mask]
    if weights is not None and len(weights) > 0:
        w = weights[below_mask]
        mean_gap = float(np.average(gaps, weights=w)) if n_below > 0 else 0.0
        total_gap = float((gaps * w).sum())
    else:
        mean_gap = float(gaps.mean()) if n_below > 0 else 0.0
        total_gap = float(gaps.sum())

    return GapAnalysis(
        target=target,
        n_below_target=n_below,
        pct_below_target=pct_below,
        mean_gap=round(mean_gap, 4),
        total_gap=round(total_gap, 4),
    )
