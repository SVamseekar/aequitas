"""Join ONS centroids to pack demographics without inventing rural flags."""

from pathlib import Path

import pandas as pd

from aequitas.analytics.centroids import (
    CENTROID_VINTAGE,
    filter_centroids_for_studio,
    write_centroids_parquet,
)


def test_write_and_join_tiny_fixture(tmp_path: Path) -> None:
    raw = pd.DataFrame(
        [
            {"LSOA21CD": "E01000011", "LAT": 52.35, "LONG": -2.45},
            {"LSOA21CD": "E01000012", "LAT": 52.48, "LONG": -1.90},
            {"LSOA21CD": "W01000001", "LAT": 51.5, "LONG": -3.2},
        ]
    )
    path = write_centroids_parquet(raw, tmp_path, source_url="https://example.test/ons")
    pts = pd.read_parquet(path)
    assert set(pts["lsoa_code"]) == {"E01000011", "E01000012"}
    demo = pd.DataFrame(
        [
            {
                "lsoa_cd": "E01000011",
                "lsoa_nm": "A",
                "population": 100,
                "imd_decile": 1,
                "region": "West Midlands",
                "urban_rural": "Rural",
            },
            {
                "lsoa_cd": "E01000012",
                "lsoa_nm": "B",
                "population": 200,
                "imd_decile": 9,
                "region": "West Midlands",
                "urban_rural": "Urban",
            },
        ]
    )
    rural = filter_centroids_for_studio(demo, pts, region="E12000005", urban_rural="rural")
    assert len(rural) == 1
    assert rural.iloc[0]["area"] == "E01000011"
    assert "2021" in CENTROID_VINTAGE
