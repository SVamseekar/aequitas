"""Tests for ML clustering."""

import numpy as np
from aequitas.analytics.ml_clustering import cluster_lsoas_hdbscan, cluster_lsoas_gmm


def test_hdbscan_returns_labels():
    np.random.seed(42)
    features = np.random.randn(1000, 5)
    labels = cluster_lsoas_hdbscan(features, min_cluster_size=50, min_samples=5)
    assert len(labels) == 1000
    assert -1 in labels  # noise expected


def test_gmm_returns_probabilities():
    np.random.seed(42)
    features = np.random.randn(1000, 5)
    probs = cluster_lsoas_gmm(features, n_components=4)
    assert probs.shape == (1000, 4)
    assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-6)
