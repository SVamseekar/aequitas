"""Tests for ml_clusters.py — covers c6, d6, g1."""
import pandas as pd
import pytest

from aequitas.warehouse.stats_builders.ml_clusters import build_ml_clusters_stats


def _route_clusters_df():
    rows = []
    # cluster 1: short local routes (n=3)
    for _ in range(3):
        rows.append({"cluster": 1, "length_km": 9.0, "stop_count": 23, "cross_la_int": 0})
    # cluster 4: long cross-boundary routes (n=2)
    for _ in range(2):
        rows.append({"cluster": 4, "length_km": 47.0, "stop_count": 47, "cross_la_int": 1})
    # noise (n=1) — must be excluded from cluster list
    rows.append({"cluster": -1, "length_km": 45.0, "stop_count": 53, "cross_la_int": 0})
    return pd.DataFrame(rows)


def _lsoa_archetype_df():
    rows = (
        [{"hdbscan_archetype": "Noise"}] * 6
        + [{"hdbscan_archetype": "Elderly Rural"}] * 3
        + [{"hdbscan_archetype": "Diverse Urban"}] * 1
    )
    return pd.DataFrame(rows)


def test_route_clusters_excludes_noise_and_has_descriptions():
    df = _route_clusters_df()
    stats = build_ml_clusters_stats("g1_route_clusters", df)
    cluster_ids = {c["id"] for c in stats["clusters"]}
    assert -1 not in cluster_ids
    assert stats["entity_type"] == "routes"
    assert stats["n_clusters"] == len(stats["clusters"])
    for c in stats["clusters"]:
        assert c["n"] > 0
        assert 0 < c["pct"] <= 100
        assert isinstance(c["description"], str) and len(c["description"]) > 0


def test_route_archetypes_uses_same_source_different_entity_type():
    df = _route_clusters_df()
    stats = build_ml_clusters_stats("c6_route_archetypes", df)
    assert stats["entity_type"] == "route archetypes"
    assert stats["n_clusters"] > 0


def test_lsoa_archetype_clusters_from_prelabelled_column():
    df = _lsoa_archetype_df()
    stats = build_ml_clusters_stats("d6_transport_poverty", df)
    assert stats["entity_type"] == "LSOAs"
    labels = {c["description"][:13] for c in stats["clusters"]}  # description starts with label
    assert any("Noise" in c["description"] for c in stats["clusters"])
    assert any("Elderly Rural" in c["description"] for c in stats["clusters"])
    total_pct = sum(c["pct"] for c in stats["clusters"])
    assert total_pct == pytest.approx(100.0, abs=0.5)


def test_empty_df_returns_empty():
    assert build_ml_clusters_stats("g1_route_clusters", pd.DataFrame()) == {}
