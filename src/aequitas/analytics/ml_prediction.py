"""Random Forest coverage prediction + SHAP feature importance.

Ported from Phase 0 notebook 04d.
Target: log1p(trips_per_capita). Back-transform with np.expm1().
Ground truth: R² = 0.472 on 33,755 LSOAs (Phase 0 audit).
Top SHAP feature: nocar_pct.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score


def train_coverage_model(
    X: pd.DataFrame,
    y: np.ndarray,
    n_estimators: int = 200,
    max_depth: int = 10,
    min_samples_leaf: int = 50,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[RandomForestRegressor, dict]:
    """Train Random Forest coverage prediction model.

    Args:
        X: Feature DataFrame (n_lsoas, n_features). Must have no NaN.
        y: Target array (trips_per_capita). Will be log1p-transformed internally.
        n_estimators: Number of trees.
        max_depth: Maximum tree depth.
        min_samples_leaf: Minimum samples per leaf.
        test_size: Fraction of data for test set.
        random_state: Random seed.

    Returns:
        Tuple of (fitted model, metrics dict).
        metrics contains: r2_train, r2_test, mae_test, rmse_test.
    """
    y_log = np.log1p(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_log, test_size=test_size, random_state=random_state
    )

    rf = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        n_jobs=-1,
        random_state=random_state,
    )
    rf.fit(X_train, y_train)

    y_pred_train = rf.predict(X_train)
    y_pred_test = rf.predict(X_test)

    metrics = {
        "r2_train": float(r2_score(y_train, y_pred_train)),
        "r2_test": float(r2_score(y_test, y_pred_test)),
        "mae_test": float(np.mean(np.abs(y_test - y_pred_test))),
        "rmse_test": float(np.sqrt(np.mean((y_test - y_pred_test) ** 2))),
        "n_train": len(X_train),
        "n_test": len(X_test),
    }
    return rf, metrics


def compute_shap_importance(
    model: RandomForestRegressor,
    X: pd.DataFrame,
    max_samples: int = 1000,
) -> pd.DataFrame:
    """Compute SHAP feature importance using TreeExplainer.

    Args:
        model: Fitted RandomForestRegressor.
        X: Feature DataFrame (used to compute SHAP values).
        max_samples: Max rows to use for SHAP computation (for speed).

    Returns:
        DataFrame with columns 'feature', 'mean_abs_shap', sorted descending.
    """
    import shap

    # Subsample for speed
    if len(X) > max_samples:
        X_sample = X.sample(n=max_samples, random_state=42)
    else:
        X_sample = X

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)

    mean_abs = np.abs(shap_values).mean(axis=0)
    importance = pd.DataFrame({
        "feature": X.columns.tolist(),
        "mean_abs_shap": mean_abs,
    }).sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)
    return importance
