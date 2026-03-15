"""ML clustering — HDBSCAN + GMM soft membership.

Ported from Phase 0 notebook 04d.
LSOA clustering: HDBSCAN (min_cluster_size=100, min_samples=10) for density-based
discovery, GMM (n_components=4) for soft probabilistic membership.
"""

import numpy as np
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

try:
    import hdbscan as _hdbscan_module
    _HDBSCAN_AVAILABLE = True
except ImportError:
    _HDBSCAN_AVAILABLE = False


def cluster_lsoas_hdbscan(
    features: np.ndarray,
    min_cluster_size: int = 100,
    min_samples: int = 10,
) -> np.ndarray:
    """Cluster LSOAs using HDBSCAN.

    StandardScaler preprocessing applied before clustering.
    Noise points (genuine heterogeneity) are labelled -1.

    Args:
        features: Feature matrix (n_lsoas, n_features).
        min_cluster_size: Minimum cluster size.
        min_samples: Core point threshold.

    Returns:
        Array of cluster labels (int). -1 = noise.
    """
    if not _HDBSCAN_AVAILABLE:
        raise ImportError("hdbscan package is required: pip install hdbscan")

    scaler = StandardScaler()
    X = scaler.fit_transform(features)

    clusterer = _hdbscan_module.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
    )
    return clusterer.fit_predict(X)


def cluster_lsoas_gmm(
    features: np.ndarray,
    n_components: int = 4,
    random_state: int = 42,
) -> np.ndarray:
    """Fit Gaussian Mixture Model for soft probabilistic cluster membership.

    StandardScaler preprocessing applied before fitting.

    Args:
        features: Feature matrix (n_lsoas, n_features).
        n_components: Number of Gaussian components.
        random_state: Random seed for reproducibility.

    Returns:
        Probability matrix (n_lsoas, n_components). Rows sum to 1.
    """
    scaler = StandardScaler()
    X = scaler.fit_transform(features)

    gmm = GaussianMixture(
        n_components=n_components,
        covariance_type="full",
        random_state=random_state,
        n_init=5,
    )
    gmm.fit(X)
    return gmm.predict_proba(X)
