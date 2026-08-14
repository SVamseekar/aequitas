"""Ticker metrics match ground-truth packing (Part E Task 3)."""
from aequitas.api.routers.metrics import _FALLBACK, _build_live_ticker


def test_fallback_equity_packing():
    by_key = {m["key"]: m for m in _FALLBACK}
    assert by_key["gini"]["value"] == "0.5741"
    assert by_key["palma"]["value"] == "5.702×"
    assert by_key["concentration_index"]["value"] == "+0.1358"


def test_live_ticker_prefers_provenance_over_truncated_section_stats():
    # section_results historically stores palma=5.7 / CI=0.1344 — must not win.
    truncated = {
        "f1_gini": {
            "gini": 0.5741,
            "palma": 5.7,
            "concentration_index": 0.1344,
        },
        "b1_frequency": {"national_avg": 65.42},
    }
    provenance = {
        "gini": 0.5741,
        "palma": 5.702,
        "concentration_index": 0.1358,
    }
    metrics = _build_live_ticker(truncated, provenance)
    by_key = {m["key"]: m for m in metrics}
    assert by_key["gini"]["value"] == "0.5741"
    assert by_key["palma"]["value"] == "5.702×"
    assert by_key["concentration_index"]["value"] == "+0.1358"
    assert by_key["mean_sqi"]["value"] == "65.4"


def test_live_ticker_falls_back_equity_when_no_provenance():
    metrics = _build_live_ticker({}, {})
    by_key = {m["key"]: m for m in metrics}
    assert by_key["palma"]["value"] == "5.702×"
    assert by_key["concentration_index"]["value"] == "+0.1358"


def test_live_ticker_does_not_reuse_national_ops_on_a_filter():
    metrics = _build_live_ticker({}, {"gini": 0.4}, allow_equity_fallback=False)
    by_key = {m["key"]: m for m in metrics}
    assert by_key["gini"]["value"] == "0.4000"
    assert by_key["evening_isolated"]["value"] == "—"
    assert by_key["sunday_deserts"]["value"] == "—"
    assert by_key["mean_sqi"]["value"] == "—"


def test_filtered_sqi_uses_value_not_national_avg():
    metrics = _build_live_ticker(
        {
            "b1_frequency": {"value": 63.44, "national_avg": 65.42},
            "b2_operating_hours": {"n_evening_isolated": 197, "pct_evening_isolated": 38.5},
            "b3_weekend_penalty": {"n_sunday_desert": 308, "pct_sunday_desert": 60.2},
        },
        {"gini": 0.4883},
        allow_equity_fallback=False,
    )
    by_key = {m["key"]: m for m in metrics}
    assert by_key["mean_sqi"]["value"] == "63.4"


def test_empty_filter_does_not_use_leaked_or_national_sqi():
    metrics = _build_live_ticker(
        {"b1_frequency": {"value": 82.21, "national_avg": 65.42}},
        {},
        allow_equity_fallback=False,
    )
    by_key = {m["key"]: m for m in metrics}
    assert by_key["mean_sqi"]["value"] == "—"
