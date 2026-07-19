"""Overview labels and severity match headline metrics (Part E Task 2)."""
from aequitas.api.routers.overview import _DIMENSION_META, _severity


def test_equity_label_is_gini_not_disparity():
    _name, label, _route = _DIMENSION_META["equity"]
    assert "gini" in label.lower()
    assert "disparity" not in label.lower()


def test_service_quality_label_is_sqi():
    _name, label, _route = _DIMENSION_META["service_quality"]
    assert "sqi" in label.lower()


def test_gini_national_is_high_severity():
    # Ground truth Gini 0.5741 must not be classified "low" (old disparity thresholds).
    assert _severity("equity", 0.5741) == "high"
    assert _severity("equity", 0.45) == "medium"
    assert _severity("equity", 0.3) == "low"


def test_accessibility_inverted():
    assert _severity("accessibility", 79.27) == "medium"
    assert _severity("accessibility", 92.0) == "low"
    assert _severity("accessibility", 60.0) == "high"


def test_service_quality_sqi_bands():
    assert _severity("service_quality", 65.42) == "low"
    assert _severity("service_quality", 55.0) == "medium"
    assert _severity("service_quality", 40.0) == "high"
