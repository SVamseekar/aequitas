"""Equity analytics — Gini, Palma, Concentration Index, vulnerability index.

Ported from Phase 0 notebook 04c.
NumPy 2.x guard: uses trapezoid with fallback to trapz.
"""

import numpy as np
import pandas as pd

# NumPy 2.x uses np.trapezoid; 1.x used np.trapz (removed in 2.x)
_trapezoid = getattr(np, "trapezoid", getattr(np, "trapz", None))
if _trapezoid is None:
    raise ImportError("NumPy has neither 'trapezoid' nor 'trapz' — unsupported version")


def compute_gini(values: np.ndarray, weights: np.ndarray) -> float:
    """Population-weighted Gini coefficient via Lorenz curve area.

    Args:
        values: Service levels per unit (e.g. trips per LSOA).
        weights: Population weights per unit.

    Returns:
        Gini coefficient in [0, 1]. 0 = perfect equality, 1 = maximum inequality.
    """
    # Sort by values ascending
    order = np.argsort(values)
    values = values[order]
    weights = weights[order]

    # Cumulative population and service shares
    cum_pop = np.cumsum(weights) / weights.sum()
    cum_service = np.cumsum(values * weights) / (values * weights).sum()

    # Insert origin (0, 0)
    cum_pop = np.concatenate([[0], cum_pop])
    cum_service = np.concatenate([[0], cum_service])

    # Gini = 1 - 2 * area under Lorenz curve
    lorenz_area = _trapezoid(cum_service, cum_pop)
    return float(1 - 2 * lorenz_area)


def compute_palma_ratio(values: np.ndarray, weights: np.ndarray) -> float:
    """Palma ratio: mean service in top 10% / mean service in bottom 40%.

    Args:
        values: Service levels per unit.
        weights: Population weights per unit.

    Returns:
        Palma ratio. Higher = more unequal.
    """
    order = np.argsort(values)
    values = values[order]
    weights = weights[order]

    cum_pop_frac = np.cumsum(weights) / weights.sum()

    # Bottom 40%
    bottom_mask = cum_pop_frac <= 0.40
    top_mask = cum_pop_frac > 0.90

    bottom_mean = np.average(values[bottom_mask], weights=weights[bottom_mask]) if bottom_mask.sum() > 0 else 0.0
    top_mean = np.average(values[top_mask], weights=weights[top_mask]) if top_mask.sum() > 0 else 0.0

    return float(top_mean / bottom_mean) if bottom_mean > 0 else float("inf")


def compute_concentration_index(service: np.ndarray, rank: np.ndarray, population: np.ndarray) -> float:
    """Wagstaff Concentration Index (CI) — covariance method.

    Positive CI = service concentrated in richer (lower deprivation rank) areas.
    Negative CI = service concentrated in poorer areas.

    Args:
        service: Service level per LSOA.
        rank: Deprivation rank (1 = most deprived, higher = less deprived).
        population: Population weights per LSOA.

    Returns:
        Concentration Index in [-1, 1].
    """
    n = len(service)
    # Fractional rank (0 to 1)
    total_pop = population.sum()
    order = np.argsort(rank)
    pop_sorted = population[order]
    frac_rank = (np.cumsum(pop_sorted) - 0.5 * pop_sorted) / total_pop

    # Sort service and pop by rank order
    service_sorted = service[order]

    mean_service = np.average(service_sorted, weights=pop_sorted)
    # CI = 2 * cov(service, fractional_rank) / mean_service
    cov = np.average((service_sorted - mean_service) * (frac_rank - 0.5), weights=pop_sorted)
    return float(2 * cov / mean_service) if mean_service > 0 else 0.0


def compute_vulnerability_index(df: pd.DataFrame) -> pd.Series:
    """5-factor vulnerability index (0-100, higher = more vulnerable).

    Factors: IMD score, % no-car, % elderly, % disability, unemployment rate.
    Each factor min-max normalised to 0-100, then equal-weighted average.

    Args:
        df: DataFrame with columns: imd_score, nocar_pct, elderly_pct,
            disability_pct, unemployment_rate.

    Returns:
        Series of vulnerability scores (0-100).
    """
    factors = ["imd_score", "nocar_pct", "elderly_pct", "disability_pct", "unemployment_rate"]
    normalised = pd.DataFrame(index=df.index)
    for col in factors:
        mn, mx = df[col].min(), df[col].max()
        normalised[col] = (df[col] - mn) / (mx - mn) * 100 if mx > mn else 0.0
    return normalised.mean(axis=1).round(2)


def identify_triple_deprived(df: pd.DataFrame) -> pd.Series:
    """Flag LSOAs in the worst tertile on 3+ deprivation dimensions.

    Dimensions: IMD score (top tertile = most deprived), no-car % (top tertile),
    elderly % (top tertile).

    Args:
        df: Master LSOA table with columns imd_score, nocar_pct, elderly_pct.

    Returns:
        Boolean Series — True if LSOA is triple-deprived.
    """
    imd_thresh = df["imd_score"].quantile(2 / 3)
    nocar_thresh = df["nocar_pct"].quantile(2 / 3)
    elderly_thresh = df["elderly_pct"].quantile(2 / 3)

    return (
        (df["imd_score"] >= imd_thresh)
        & (df["nocar_pct"] >= nocar_thresh)
        & (df["elderly_pct"] >= elderly_thresh)
    )
