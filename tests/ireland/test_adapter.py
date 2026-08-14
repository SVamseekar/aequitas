"""Ireland adapter: 2 SAs, 1 stop → 400 m / band / score. No England numbers."""

import pandas as pd

from aequitas.analytics.bands import assign_service_band
from aequitas.analytics.score import compute_score
from aequitas.ireland.process import build_ireland_areas
from aequitas.ireland.warehouse import build_ireland_warehouse, precompute_ireland


def _fixture():
    areas = pd.DataFrame(
        [
            {
                "sa_code": "SA001",
                "name": "Cork test SA",
                "lat": 51.898,
                "lon": -8.475,
                "population": 400,
                "hp_relative": -12.0,
                "region": "cork",
                "area_km2": 0.4,
            },
            {
                "sa_code": "SA002",
                "name": "Remote SA",
                "lat": 52.15,
                "lon": -9.55,
                "population": 300,
                "hp_relative": 8.0,
                "region": "kerry",
                "area_km2": 12.0,
            },
        ]
    )
    stops = pd.DataFrame(
        [{"stop_id": "TFI1", "stop_name": "Cork stop", "stop_lat": 51.8981, "stop_lon": -8.4751}]
    )
    return build_ireland_areas(areas=areas, stops=stops)


def test_join_two_sas_one_stop_400m():
    built = _fixture()
    cork = built.loc[built["sa_code"] == "SA001"].iloc[0]
    remote = built.loc[built["sa_code"] == "SA002"].iloc[0]
    assert cork["within_400m"]
    assert cork["stop_count"] >= 1
    assert not remote["within_400m"]
    assert remote["stop_count"] == 0


def test_service_band_on_fixture():
    built = _fixture()
    cork = built.loc[built["sa_code"] == "SA001"].iloc[0]
    remote = built.loc[built["sa_code"] == "SA002"].iloc[0]
    b_remote, _ = assign_service_band(
        stop_count=remote["stop_count"],
        no_service=remote["no_service"],
        evening_isolated=remote["evening_isolated"],
        sunday_desert=remote["sunday_desert"],
        sqi=remote["sqi"],
    )
    assert b_remote == 1
    b_near, _ = assign_service_band(
        stop_count=1,
        no_service=False,
        evening_isolated=True,
        sunday_desert=True,
        sqi=40.0,
    )
    assert b_near == 2


def test_score_from_ireland_terms_not_england():
    built = _fixture()
    pop = float(built["population"].sum())
    covered = float(built.loc[built["within_400m"], "population"].sum()) / pop
    result = compute_score(
        {
            "pop_within_400m": covered,
            "evening_served": 0.0,
            "weekday_frequency": 0.2,
            "deprivation_service": 0.5,
        },
        n_areas=2,
        region="cork",
        urban_rural="all",
    )
    assert result.score is not None
    assert result.score != 80.0


def test_warehouse_sections_have_hp_not_imd_labels(tmp_path):
    built = _fixture()
    dest = tmp_path / "aequitas_ireland.duckdb"
    build_ireland_warehouse(built, dest)
    rows = precompute_ireland(built)
    d1 = next(r for r in rows if r["section_id"] == "d1_coverage_deprivation" and r["region"] == "all")
    assert "HP" in (d1["stats"].get("x_label") or "")
    assert "IMD" not in (d1["stats"].get("x_label") or "")
    bsa = next(r for r in rows if r["section_id"] == "bsa1_franchising_readiness")
    assert bsa["stats"].get("not_applicable") is not True
    prog = (bsa["stats"].get("programme") or bsa["narrative"] or "")
    assert "Connecting Ireland" in prog or "NTA" in prog
    from aequitas.ireland.sections import CATALOGUE, catalogue_counts

    counts = catalogue_counts()
    assert counts["answers"] == len(CATALOGUE)
    assert counts["same"] + counts["replace"] + counts["omit"] == counts["answers"]
    ids = {r["section_id"] for r in rows if r["region"] == "all" and r["urban_rural"] == "all"}
    assert ids == set(CATALOGUE)
