"""2SFCA accessibility — Two-Step Floating Catchment Area.

Ported from Phase 0 notebook 04d.
Standard NHS/DfT accessibility metric using BNG coordinates (metres).
Step 1: R_j = trips_j / pop_within_catchment_j  (supply ratio per stop)
Step 2: A_i = sum(R_j for stops within catchment of LSOA i)
Ground truth: 6,776 LSOAs with 2SFCA score = 0 (no stop within 400m).
"""

import numpy as np
from scipy.spatial import cKDTree


def compute_2sfca(
    demand_points: np.ndarray,
    demand_pop: np.ndarray,
    supply_points: np.ndarray,
    supply_capacity: np.ndarray,
    catchment_m: float = 400.0,
) -> np.ndarray:
    """Two-Step Floating Catchment Area accessibility score.

    Uses Euclidean distance in metric coordinates (e.g. BNG eastings/northings).
    Score is proportional to trips-per-person within the catchment.

    Step 1: For each supply point j, compute supply ratio
        R_j = capacity_j / sum(demand_pop for demand points within catchment_m)
        If no demand within catchment, R_j = 0.

    Step 2: For each demand point i, sum supply ratios within catchment_m
        A_i = sum(R_j for supply points j within catchment_m of i)

    Args:
        demand_points: Array shape (n_demand, 2) — coordinates of LSOA centroids.
        demand_pop: Array shape (n_demand,) — population at each demand point.
        supply_points: Array shape (n_supply, 2) — coordinates of bus stops/POIs.
        supply_capacity: Array shape (n_supply,) — service capacity (e.g. weekly trips).
        catchment_m: Distance threshold in same units as coordinates (default 400m).

    Returns:
        Array shape (n_demand,) of 2SFCA accessibility scores. 0 = no access.
    """
    demand_tree = cKDTree(demand_points)
    supply_tree = cKDTree(supply_points)

    # Step 1: supply ratio R_j for each supply point
    # Find all demand points within catchment of each supply point
    supply_ratios = np.zeros(len(supply_points))
    for j, supply_coord in enumerate(supply_points):
        demand_idxs = demand_tree.query_ball_point(supply_coord, r=catchment_m)
        pop_in_catchment = demand_pop[demand_idxs].sum() if demand_idxs else 0.0
        supply_ratios[j] = (
            float(supply_capacity[j]) / pop_in_catchment
            if pop_in_catchment > 0
            else 0.0
        )

    # Step 2: A_i = sum of R_j for supply points within catchment of each demand point
    scores = np.zeros(len(demand_points))
    for i, demand_coord in enumerate(demand_points):
        supply_idxs = supply_tree.query_ball_point(demand_coord, r=catchment_m)
        if supply_idxs:
            scores[i] = supply_ratios[supply_idxs].sum()

    return scores


def normalise_scores(scores: np.ndarray) -> np.ndarray:
    """Min-max normalise 2SFCA scores to 0-100.

    Args:
        scores: Raw 2SFCA scores from compute_2sfca.

    Returns:
        Array of scores normalised to 0-100.
    """
    s_max = scores.max()
    if s_max == 0:
        return np.zeros_like(scores)
    return np.round(scores / s_max * 100, 2)
