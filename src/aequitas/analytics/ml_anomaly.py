"""ML anomaly detection — Isolation Forest + LOF.

Ported from Phase 0 notebook 04d.
Ground truth: 1,688 anomalies (5% of 33,755 LSOAs).
Anomaly types: positive_deprived_well_served, inefficiency_affluent_poor_served,
policy_failure_elderly_no_service, other_anomaly, normal.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler


def detect_anomalies(
    df: pd.DataFrame,
    feature_cols: list[str],
    contamination: float = 0.05,
    n_estimators: int = 200,
    lof_neighbors: int = 20,
    random_state: int = 42,
) -> pd.DataFrame:
    """Detect anomalous LSOAs using Isolation Forest + LOF ensemble.

    StandardScaler preprocessing applied before both algorithms.
    An LSOA is flagged if detected by either algorithm (iso_anomaly or lof_anomaly).
    both_anomaly=True if flagged by both.

    Args:
        df: LSOA DataFrame. Must contain feature_cols with no NaN.
        feature_cols: Feature columns to use for anomaly detection.
        contamination: Expected fraction of anomalies (default 0.05 = 5%).
        n_estimators: Number of trees for Isolation Forest.
        lof_neighbors: Number of neighbours for LOF.
        random_state: Random seed for Isolation Forest.

    Returns:
        DataFrame with columns iso_anomaly, iso_score, lof_anomaly, lof_score,
        both_anomaly, anomaly_type appended to input df.
    """
    X = df[feature_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Isolation Forest
    iso = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,
    )
    iso_labels = iso.fit_predict(X_scaled)  # -1 = anomaly, 1 = normal
    iso_scores = iso.score_samples(X_scaled)  # lower = more anomalous

    # LOF (novelty=False for unsupervised)
    lof = LocalOutlierFactor(
        n_neighbors=lof_neighbors,
        contamination=contamination,
        n_jobs=-1,
    )
    lof_labels = lof.fit_predict(X_scaled)  # -1 = anomaly, 1 = normal
    lof_scores = lof.negative_outlier_factor_  # lower = more anomalous

    result = df.copy()
    result["iso_anomaly"] = iso_labels == -1
    result["iso_score"] = iso_scores.astype(float)
    result["lof_anomaly"] = lof_labels == -1
    result["lof_score"] = lof_scores.astype(float)
    result["both_anomaly"] = result["iso_anomaly"] & result["lof_anomaly"]

    result["anomaly_type"] = _classify_anomaly_type(result)
    return result


def _classify_anomaly_type(df: pd.DataFrame) -> pd.Series:
    """Classify anomaly type based on deprivation and service patterns.

    Types:
    - positive_deprived_well_served: deprived (imd_decile ≤ 3) + high service
    - inefficiency_affluent_poor_served: affluent (imd_decile ≥ 8) + low service
    - policy_failure_elderly_no_service: high elderly% + zero/near-zero service
    - other_anomaly: flagged by either algorithm but not in above categories
    - normal: not flagged
    """
    flagged = df["iso_anomaly"] | df["lof_anomaly"]

    # Require these columns for classification; fall back to other_anomaly if absent
    has_imd = "imd_decile" in df.columns
    has_sqi = "service_quality_index" in df.columns
    has_elderly = "elderly_pct" in df.columns
    has_trips = "trips_per_capita" in df.columns

    anomaly_type = pd.Series("normal", index=df.index)

    if has_imd and has_sqi:
        sqi_high = df["service_quality_index"] > df["service_quality_index"].quantile(0.75)
        sqi_low = df["service_quality_index"] < df["service_quality_index"].quantile(0.25)

        pos_mask = flagged & (df["imd_decile"] <= 3) & sqi_high
        ineff_mask = flagged & (df["imd_decile"] >= 8) & sqi_low
        anomaly_type[pos_mask] = "positive_deprived_well_served"
        anomaly_type[ineff_mask] = "inefficiency_affluent_poor_served"

    if has_elderly and has_trips:
        policy_mask = (
            flagged
            & (df["elderly_pct"] > df["elderly_pct"].quantile(0.90))
            & (df["trips_per_capita"] < 0.01)
            & (anomaly_type == "normal")
        )
        anomaly_type[policy_mask] = "policy_failure_elderly_no_service"

    # Remaining flagged LSOAs
    other_mask = flagged & (anomaly_type == "normal")
    anomaly_type[other_mask] = "other_anomaly"

    return anomaly_type
