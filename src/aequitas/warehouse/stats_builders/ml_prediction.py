"""Stats builder for ml_prediction.j2 — Random Forest R² / SHAP feature importance.

Covers: a8_coverage_prediction, d8_feature_importance, g3_coverage_model, g4_shap.

The model is trained once nationally — these stats are identical across every
filter combination (region/urban_rural make no difference to a nationally-fit
model's R² or SHAP values). This is documented behaviour per ISSUES.md §4.3,
not a bug: the narrative caveat about national-vs-regional applicability lives
in the template/registry layer, not here.
"""

import pandas as pd


def build_ml_prediction_stats(section_id: str, shap_df: pd.DataFrame, r2: float | None) -> dict:
    """Build stats for any ml_prediction.j2-backed section.

    Args:
        section_id: One of a8_coverage_prediction, d8_feature_importance,
            g3_coverage_model, g4_shap. (Accepted for interface symmetry with
            other builders and potential future per-section framing — all four
            currently return the same national-model stats.)
        shap_df: DataFrame loaded from shap_summary.csv with columns
            'feature' and 'mean_abs_shap'.
        r2: Confirmed R² figure for the national Random Forest model
            (0.4719 — see docs/figures-registry.md ST-007).

    Returns:
        Dict with r2, top_feature, top_importance, n_features, or {} if the
        SHAP data or R² figure is unavailable.
    """
    if shap_df.empty or "feature" not in shap_df.columns or "mean_abs_shap" not in shap_df.columns:
        return {}
    if r2 is None:
        return {}

    ranked = shap_df.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)
    top = ranked.iloc[0]

    return {
        "r2": round(float(r2), 4),
        "top_feature": str(top["feature"]),
        "top_importance": round(float(top["mean_abs_shap"]), 3),
        "n_features": int(len(ranked)),
    }
