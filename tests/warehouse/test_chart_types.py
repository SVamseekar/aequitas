"""Verify every section's chart_data.type matches a frontend ChartRenderer case."""
import duckdb
import pytest

FRONTEND_CHART_TYPES = {
    "horizontal_bar", "grouped_bar", "stacked_bar",
    "scatter_regression", "lorenz_curve", "shap_bar",
    "choropleth", "heatmap", "box_violin", "scatter_clusters",
    "kpi_tiles", "table",
}


@pytest.fixture
def db():
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent  # tests/warehouse/ → tests/ → root
    db_path = project_root / "data" / "aequitas.duckdb"
    if not db_path.exists():
        pytest.skip(f"Warehouse not built yet: {db_path}")
    conn = duckdb.connect(str(db_path), read_only=True)
    yield conn
    conn.close()


def test_all_chart_types_recognized(db):
    """Every chart_data.type in the warehouse must match a frontend case."""
    rows = db.execute("""
        SELECT DISTINCT section_id, chart_data->>'type' AS chart_type
        FROM section_results
        WHERE chart_data IS NOT NULL AND chart_data != '{}'
    """).fetchall()
    unrecognized = [
        (sid, ct) for sid, ct in rows
        if ct is not None and ct not in FRONTEND_CHART_TYPES
    ]
    assert unrecognized == [], f"Unrecognized chart types: {unrecognized}"


def test_no_null_chart_types(db):
    """Sections with chart_data should always have a type field."""
    rows = db.execute("""
        SELECT section_id, chart_data
        FROM section_results
        WHERE chart_data IS NOT NULL
          AND chart_data != '{}'
          AND (chart_data->>'type') IS NULL
    """).fetchall()
    assert rows == [], f"Sections missing chart_data.type: {[r[0] for r in rows]}"


def test_chart_type_variety(db):
    """At least 6 different chart types should be used across sections."""
    rows = db.execute("""
        SELECT DISTINCT chart_data->>'type' AS ct
        FROM section_results
        WHERE chart_data IS NOT NULL AND chart_data != '{}'
    """).fetchall()
    types_used = {r[0] for r in rows if r[0]}
    assert len(types_used) >= 6, f"Only {len(types_used)} chart types used: {types_used}"
