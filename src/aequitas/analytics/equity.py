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


def _validate_weighted_input(
    values: np.ndarray, weights: np.ndarray, *, allow_negative_values: bool = False
) -> None:
    if values.shape != weights.shape:
        raise ValueError("values and weights must have the same shape")
    if values.size == 0:
        raise ValueError("values and weights must not be empty")
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(weights)):
        raise ValueError("values and weights must be finite")
    if np.any(weights < 0):
        raise ValueError("weights must be non-negative")
    if weights.sum() <= 0:
        raise ValueError("total weight must be positive")
    if not allow_negative_values and np.any(values < 0):
        raise ValueError("values must be non-negative")


def compute_gini(values: np.ndarray, weights: np.ndarray) -> float:
    """Population-weighted Gini coefficient via Lorenz curve area.

    Args:
        values: Service levels per unit (e.g. trips per LSOA).
        weights: Population weights per unit.

    Returns:
        Gini coefficient in [0, 1]. 0 = perfect equality, 1 = maximum
        inequality. By convention, zero total service (nothing to
        distribute) is treated as perfect equality and returns 0.0.
    """
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    _validate_weighted_input(values, weights)

    total_service = (values * weights).sum()
    if total_service == 0:
        return 0.0

    # Sort by values ascending
    order = np.argsort(values, kind="stable")
    values = values[order]
    weights = weights[order]

    # Cumulative population and service shares
    cum_pop = np.cumsum(weights) / weights.sum()
    cum_service = np.cumsum(values * weights) / total_service

    # Insert origin (0, 0)
    cum_pop = np.concatenate([[0], cum_pop])
    cum_service = np.concatenate([[0], cum_service])

    # Gini = 1 - 2 * area under Lorenz curve
    lorenz_area = _trapezoid(cum_service, cum_pop)
    return float(1 - 2 * lorenz_area)


def compute_palma_ratio(values: np.ndarray, weights: np.ndarray) -> float:
    """Palma ratio: mean service in top 10% / mean service in bottom 40%.

    Areas whose population straddles the 40%/90% cumulative-population cuts
    are split proportionally, so the result doesn't depend on how finely the
    input is divided into areas or on tie ordering.

    Args:
        values: Service levels per unit.
        weights: Population weights per unit.

    Returns:
        Palma ratio. Higher = more unequal.
    """
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    _validate_weighted_input(values, weights)

    order = np.argsort(values, kind="stable")
    values = values[order]
    weights = weights[order]

    total = weights.sum()
    cum_weight = np.cumsum(weights)
    cum_before = cum_weight - weights

    bottom_cut = 0.40 * total
    top_cut = 0.90 * total

    bottom_overlap = np.clip(np.minimum(cum_weight, bottom_cut) - cum_before, 0, None)
    top_overlap = np.clip(cum_weight - np.maximum(cum_before, top_cut), 0, None)

    bottom_weight = bottom_overlap.sum()
    top_weight = top_overlap.sum()

    bottom_mean = float(np.sum(values * bottom_overlap) / bottom_weight) if bottom_weight > 0 else 0.0
    top_mean = float(np.sum(values * top_overlap) / top_weight) if top_weight > 0 else 0.0

    return float(top_mean / bottom_mean) if bottom_mean > 0 else float("inf")


def compute_concentration_index(service: np.ndarray, rank: np.ndarray, population: np.ndarray) -> float:
    """Wagstaff Concentration Index (CI) — covariance method.

    Positive CI = service concentrated in richer (lower deprivation rank) areas.
    Negative CI = service concentrated in poorer areas.

    Units that tie on ``rank`` share the population-weighted average
    fractional rank of their tied group, so the result doesn't depend on
    the arbitrary order ties happen to appear in.

    Args:
        service: Service level per LSOA.
        rank: Deprivation rank (1 = most deprived, higher = less deprived).
        population: Population weights per LSOA.

    Returns:
        Concentration Index in [-1, 1].
    """
    service = np.asarray(service, dtype=float)
    rank = np.asarray(rank, dtype=float)
    population = np.asarray(population, dtype=float)
    _validate_weighted_input(service, population, allow_negative_values=True)
    if rank.shape != service.shape:
        raise ValueError("rank must have the same shape as service")
    if not np.all(np.isfinite(rank)):
        raise ValueError("rank must be finite")

    total_pop = population.sum()
    order = np.argsort(rank, kind="stable")
    rank_sorted = rank[order]
    pop_sorted = population[order]
    service_sorted = service[order]

    frac_rank = (np.cumsum(pop_sorted) - 0.5 * pop_sorted) / total_pop

    _, inverse, _ = np.unique(rank_sorted, return_inverse=True, return_counts=True)
    inverse = inverse.reshape(-1)
    group_pop_sum = np.zeros(inverse.max() + 1)
    group_frac_sum = np.zeros(inverse.max() + 1)
    np.add.at(group_pop_sum, inverse, pop_sorted)
    np.add.at(group_frac_sum, inverse, frac_rank * pop_sorted)
    frac_rank = (group_frac_sum / group_pop_sum)[inverse]

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
