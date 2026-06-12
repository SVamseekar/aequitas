"""Chart data builder — pure functions that produce typed JSON payloads.

Each function takes a DataFrame (or pre-aggregated data) and returns a dict
matching one of the chart_data schemas defined in the spec. The frontend
consumes these directly from the section_results.chart_data JSON column.

All scatter charts are sampled to max_points to keep storage reasonable.
All choropleths use LAD-level aggregation (not LSOA).
"""

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

# Colorblind-safe palette (Viridis-derived)
_CLUSTER_COLOURS = [
    "#440154", "#46327e", "#365c8d", "#277f8e",
    "#1fa187", "#4ac16d", "#9fda3a", "#fde725",
]


def build_horizontal_bar(
    data: pd.DataFrame,
    title: str,
    x_label: str,
    y_label: str,
    national_avg: float | None = None,
) -> dict[str, Any]:
    """Build horizontal bar chart data, sorted descending by value."""
    sorted_df = data.sort_values("value", ascending=False).reset_index(drop=True)
    items = []
    for i, row in sorted_df.iterrows():
        items.append({
            "label": str(row["label"]),
            "value": round(float(row["value"]), 4),
            "rank": i + 1,
        })
    result: dict[str, Any] = {
        "type": "horizontal_bar",
        "title": title,
        "x_label": x_label,
        "y_label": y_label,
        "data": items,
    }
    if national_avg is not None:
        result["national_avg"] = round(float(national_avg), 4)
    return result


def build_scatter_regression(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    id_col: str,
    title: str,
    x_label: str,
    y_label: str,
    max_points: int = 2000,
) -> dict[str, Any]:
    """Build scatter plot with regression line. Samples to max_points for display."""
    clean = df[[x_col, y_col, id_col]].dropna()
    n = len(clean)

    # Compute stats on full data
    r, p_value = scipy_stats.pearsonr(clean[x_col], clean[y_col]) if n >= 3 else (0.0, 1.0)
    slope, intercept = np.polyfit(clean[x_col], clean[y_col], 1) if n >= 2 else (0.0, 0.0)

    # Sample for display
    if n > max_points:
        sample = clean.sample(n=max_points, random_state=42)
    else:
        sample = clean

    points = [
        {"x": round(float(row[x_col]), 4), "y": round(float(row[y_col]), 4), "id": str(row[id_col])}
        for _, row in sample.iterrows()
    ]

    return {
        "type": "scatter_regression",
        "title": title,
        "x_label": x_label,
        "y_label": y_label,
        "r": round(float(r), 4),
        "p_value": round(float(p_value), 6),
        "regression_line": {"slope": round(float(slope), 6), "intercept": round(float(intercept), 6)},
        "sample_size": n,
        "display_sample_size": len(points),
        "data": points,
    }


def build_lorenz_curve(
    values: pd.Series,
    weights: pd.Series,
    title: str,
    reference_gini: float = 0.36,
    reference_label: str = "UK Income Gini",
    n_points: int = 100,
) -> dict[str, Any]:
    """Build Lorenz curve with Gini coefficient."""
    sorted_idx = values.argsort()
    sorted_vals = values.iloc[sorted_idx].values
    sorted_weights = weights.iloc[sorted_idx].values

    cum_pop = np.cumsum(sorted_weights) / sorted_weights.sum()
    weighted_vals = sorted_vals * sorted_weights
    cum_service = np.cumsum(weighted_vals) / weighted_vals.sum()

    # Prepend origin
    cum_pop = np.concatenate([[0], cum_pop])
    cum_service = np.concatenate([[0], cum_service])

    # Gini from Lorenz curve
    trapezoid = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
    area_under = float(trapezoid(cum_service, cum_pop))
    gini = round(1 - 2 * area_under, 4)

    # Downsample curve points
    indices = np.linspace(0, len(cum_pop) - 1, n_points, dtype=int)
    curve_points = [
        {"cum_pop": round(float(cum_pop[i]), 4), "cum_service": round(float(cum_service[i]), 4)}
        for i in indices
    ]

    return {
        "type": "lorenz_curve",
        "title": title,
        "gini": gini,
        "reference_gini": reference_gini,
        "reference_label": reference_label,
        "curve_points": curve_points,
    }


def build_stacked_bar(
    categories: list[str],
    series: list[dict[str, Any]],
    title: str,
) -> dict[str, Any]:
    """Build stacked bar chart data."""
    return {
        "type": "stacked_bar",
        "title": title,
        "categories": categories,
        "series": series,
    }


def build_grouped_bar(
    categories: list[str],
    series: list[dict[str, Any]],
    title: str,
) -> dict[str, Any]:
    """Build grouped bar chart data."""
    return {
        "type": "grouped_bar",
        "title": title,
        "categories": categories,
        "series": series,
    }


def build_kpi_tiles(tiles: list[dict[str, Any]], title: str) -> dict[str, Any]:
    """Build a small grid of headline-figure KPI tiles.

    Each tile is `{"label": str, "value": int | float, "unit": str}`. Tiles
    have independent units and are NOT plotted on a shared axis — use this
    for single-scenario summaries (e.g. population affected, annual cost,
    CO2 saved) where the metrics are not directly comparable.

    Args:
        tiles: List of tile dicts, each with "label", "value", "unit".
        title: Section title shown above the tile grid.

    Returns:
        `{"type": "kpi_tiles", "title": ..., "tiles": [...]}`.
    """
    return {
        "type": "kpi_tiles",
        "title": title,
        "tiles": tiles,
    }


def build_gauge(
    markers: list[dict[str, Any]],
    bands: list[dict[str, Any]],
    title: str,
    unit: str,
    reference_lines: list[float] | None = None,
) -> dict[str, Any]:
    """Build a banded gauge chart showing one or more values against threshold zones.

    Used for headline "is this good or bad" metrics (e.g. BCR vs HM Treasury
    Green Book VfM bands, or HHI vs standard market-concentration thresholds)
    where the value's position relative to standard bands is the policy
    question, not just the raw number.

    Args:
        markers: List of `{"label": str, "value": float}` — one per region or
            scenario, plotted on the same banded scale.
        bands: Ordered list of `{"label": str, "min": float, "max": float | None,
            "color_hint": str}` describing threshold zones. `max: None` means
            the band is open-ended (extends to infinity).
        title: Section title shown above the gauge.
        unit: Axis unit label (e.g. "BCR" or "HHI").
        reference_lines: Optional list of x-values to draw as vertical
            reference lines (e.g. BCR break-even at 1.0).

    Returns:
        `{"type": "gauge", "title": ..., "unit": ..., "bands": [...],
        "markers": [...], "reference_lines": [...]}`.
    """
    return {
        "type": "gauge",
        "title": title,
        "unit": unit,
        "bands": bands,
        "markers": markers,
        "reference_lines": reference_lines or [],
    }


def build_table(
    columns: list[str],
    rows: list[dict[str, Any]],
    title: str,
) -> dict[str, Any]:
    """Build a generic ranked table chart payload.

    Args:
        columns: Ordered list of column header labels, matching keys in `rows`.
        rows: List of row dicts, one per record, keyed by column name.
        title: Section title shown above the table.

    Returns:
        `{"type": "table", "title": ..., "columns": [...], "data": [...]}`.
        `data` is consumed directly by the frontend `DataTable` component.
    """
    return {
        "type": "table",
        "title": title,
        "columns": columns,
        "data": rows,
    }


def build_box_violin(
    groups: dict[str, pd.Series],
    title: str,
    unit: str = "",
) -> dict[str, Any]:
    """Build box + violin chart data from grouped series."""
    group_data = []
    for label, values in groups.items():
        q1 = float(values.quantile(0.25))
        q3 = float(values.quantile(0.75))
        iqr = q3 - q1
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr
        outliers = values[(values < lower_fence) | (values > upper_fence)].tolist()
        group_data.append({
            "label": label,
            "min": round(float(values.min()), 2),
            "q1": round(q1, 2),
            "median": round(float(values.median()), 2),
            "q3": round(q3, 2),
            "max": round(float(values.max()), 2),
            "outliers": [round(float(o), 2) for o in outliers[:50]],  # cap outlier list
        })
    return {
        "type": "box_violin",
        "title": title,
        "unit": unit,
        "groups": group_data,
    }


def build_choropleth(
    data: pd.DataFrame,
    title: str,
    geography: str,
    metric: str,
    colour_scale: str = "Viridis",
) -> dict[str, Any]:
    """Build choropleth map data (LAD-aggregated, not LSOA)."""
    points = [
        {
            "area_code": str(row["area_code"]),
            "area_name": str(row.get("area_name", "")),
            "value": round(float(row["value"]), 2),
        }
        for _, row in data.iterrows()
    ]
    return {
        "type": "choropleth",
        "title": title,
        "geography": geography,
        "metric": metric,
        "colour_scale": colour_scale,
        "data": points,
    }


def build_heatmap(
    x_labels: list[str],
    y_labels: list[str],
    values: list[list[float]],
    title: str,
    colour_scale: str = "Viridis",
) -> dict[str, Any]:
    """Build heatmap data (e.g. IMD decile × urban/rural)."""
    return {
        "type": "heatmap",
        "title": title,
        "x_labels": x_labels,
        "y_labels": y_labels,
        "values": [[round(float(v), 2) for v in row] for row in values],
        "colour_scale": colour_scale,
    }


def build_shap_bar(
    features: pd.DataFrame,
    title: str,
    model_r2: float | None = None,
) -> dict[str, Any]:
    """Build SHAP feature importance bar chart."""
    sorted_df = features.sort_values("importance", ascending=False)
    items = [
        {"name": str(row["feature"]), "importance": round(float(row["importance"]), 4)}
        for _, row in sorted_df.iterrows()
    ]
    result: dict[str, Any] = {
        "type": "shap_bar",
        "title": title,
        "features": items,
    }
    if model_r2 is not None:
        result["model_r2"] = round(float(model_r2), 4)
    return result


def build_scatter_clusters(
    data: pd.DataFrame,
    cluster_labels: dict[int, str],
    title: str,
    x_label: str = "PC1",
    y_label: str = "PC2",
    max_points: int = 2000,
) -> dict[str, Any]:
    """Build scatter plot coloured by cluster membership.

    Cluster sizes (`n`) are computed from the full ``data`` frame, before any
    sampling, so the reported counts reflect true cluster membership even
    when the plotted points are subsampled for performance.
    """
    n = len(data)
    if n > max_points:
        sample = data.sample(n=max_points, random_state=42)
    else:
        sample = data

    cluster_counts = {int(k): int(v) for k, v in data["cluster"].value_counts().items()}

    clusters = [
        {
            "id": int(cid),
            "label": label,
            "colour": _CLUSTER_COLOURS[int(cid) % len(_CLUSTER_COLOURS)],
            "n": cluster_counts.get(int(cid), 0),
        }
        for cid, label in sorted(cluster_labels.items())
    ]

    cluster_sizes = [{"label": c["label"], "n": c["n"]} for c in clusters]

    points = [
        {
            "x": round(float(row["x"]), 4),
            "y": round(float(row["y"]), 4),
            "cluster": int(row["cluster"]),
            "id": str(row["id"]),
        }
        for _, row in sample.iterrows()
    ]

    return {
        "type": "scatter_clusters",
        "title": title,
        "x_label": x_label,
        "y_label": y_label,
        "clusters": clusters,
        "cluster_sizes": cluster_sizes,
        "data": points,
    }
