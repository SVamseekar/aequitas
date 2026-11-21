"""Reach must keep current-only calculations and origin filters explicit."""

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from aequitas.api.app import create_app
from aequitas.api.services import reach_query


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/reach",
        "/api/reach/bands",
        "/api/export/pack.csv",
        "/api/export/pack.html",
        "/api/export/pack.json",
    ],
)
def test_rejects_historical_cache_under_dated_label(
    endpoint: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aequitas.warehouse import packs

    monkeypatch.setattr(
        packs, "resolve_pack", lambda *args: {"current": False, "pack_id": "2020-01-01"}
    )
    response = TestClient(create_app()).get(endpoint, params={"pack": "2020-01-01"})
    assert response.status_code == 400
    assert "current" in response.json()["detail"].lower()


def test_reach_filters_origins_with_official_area_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reach = pd.DataFrame(
        {
            "lsoa": ["a", "b", "c"],
            "region": ["E12000005"] * 3,
            "dest_type": ["jobs"] * 3,
            "t_15": [0, 1, 2],
            "t_30": [0, 5, 50],
            "t_45": [0, 10, 100],
        }
    )
    bands = pd.DataFrame({"lsoa": ["a", "b", "c"], "urban_rural_norm": ["urban", "urban", "rural"]})
    monkeypatch.setattr(reach_query, "load_reach_frame", lambda **kwargs: reach)
    monkeypatch.setattr(reach_query, "load_bands_frame", lambda **kwargs: bands)
    result = reach_query.query_reach("jobs", 45, "E12000005", "urban")
    assert result["n_areas"] == 2
    assert result["median"] == 5  # Zero-count origins stay in the denominator.
    assert sum(row["n"] for row in result["histogram"]) == 2


def test_missing_origin_classification_cannot_return_all_area_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        reach_query,
        "load_reach_frame",
        lambda **kwargs: pd.DataFrame(
            {
                "lsoa": ["a"],
                "region": ["E12000005"],
                "dest_type": ["jobs"],
                "t_15": [1],
                "t_30": [2],
                "t_45": [3],
            }
        ),
    )
    monkeypatch.setattr(reach_query, "load_bands_frame", lambda **kwargs: pd.DataFrame())
    result = reach_query.query_reach("jobs", 45, "all", "rural")
    assert result["available"] is False
    assert result["median"] is None
    assert "classification" in result["note"].lower()


def test_missing_bands_read_does_not_build_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aequitas.analytics import bands
    from aequitas.core.config import PipelineConfig

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("GET must not generate user-owned band files")

    monkeypatch.setattr(bands, "write_access_bands", forbidden)
    cfg = PipelineConfig(processed_dir=tmp_path, raw_dir=tmp_path / "raw")
    assert reach_query.load_bands_frame(cfg).empty
    assert not list(Path(tmp_path).rglob("*.parquet"))
