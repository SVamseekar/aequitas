"""400 m facility access — people near official dests, not stop 400 m."""

import pandas as pd

from aequitas.analytics.destinations import facility_400m, write_facility_400m


def test_facility_400m_counts_near_and_far() -> None:
    # ~111 m per 0.001 deg lat. 0.001 ≈ 111 m; 0.01 ≈ 1.1 km.
    areas = pd.DataFrame(
        {
            "area_id": ["A", "B"],
            "lat": [53.0, 53.0],
            "lon": [-6.0, -6.0],
            "population": [100.0, 50.0],
        }
    )
    dests = pd.DataFrame(
        {
            "dest_id": ["g1"],
            "dest_type": ["gp"],
            "lat": [53.001],
            "lon": [-6.0],
            "weight": [1.0],
        }
    )
    # Put B 0.02 deg south (~2.2 km)
    areas.loc[1, "lat"] = 52.98
    out = facility_400m(areas, dests, country="ireland", dest_type="gp")
    assert out["n_areas"] == 2
    assert out["n_within_400m"] == 1
    assert abs(out["people_share"] - (100 / 150)) < 1e-6
    assert out["dest_type"] == "gp"
    assert "lsoa" not in out


def test_write_facility_400m_is_country_keyed(tmp_path) -> None:
    areas = pd.DataFrame(
        {"area_id": ["IRIS1"], "lat": [48.85], "lon": [2.35], "population": [10.0]}
    )
    dests = pd.DataFrame(
        {"dest_id": ["s1"], "dest_type": "school", "lat": [48.8505], "lon": [2.35], "weight": [1.0]}
    )
    path = write_facility_400m(tmp_path, "france", "school", areas, dests)
    assert path == tmp_path / "france" / "facility_400m_school.parquet"
    written = pd.read_parquet(path)
    assert int(written["n_within"].iloc[0]) >= 1
    assert "lsoa_code" not in written.columns
