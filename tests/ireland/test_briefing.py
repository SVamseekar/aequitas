"""Ireland briefing: distinct exhibits, omit has no chart, narratives name the filter."""

from aequitas.ireland.sections import CATALOGUE, OMIT, precompute_ireland
from aequitas.ireland.process import build_ireland_areas
import pandas as pd


def _areas():
    rows = []
    for i, (sa, region, urban, pop, hp, trips, lat, lon) in enumerate(
        [
            ("SA001", "cork", "urban", 400, -12.0, 8.0, 51.90, -8.47),
            ("SA002", "cork", "rural", 300, 4.0, 0.0, 51.80, -8.90),
            ("SA003", "dublin", "urban", 500, -20.0, 20.0, 53.35, -6.26),
            ("SA004", "dublin", "urban", 450, 10.0, 0.0, 53.32, -6.30),
            ("SA005", "kerry", "rural", 200, 6.0, 0.0, 52.06, -9.51),
            ("SA006", "kerry", "rural", 180, -4.0, 1.0, 52.10, -9.40),
        ]
    ):
        rows.append(
            {
                "sa_code": sa,
                "name": sa,
                "lat": lat,
                "lon": lon,
                "population": pop,
                "hp_relative": hp,
                "region": region,
                "area_km2": 0.5 if urban == "urban" else 8.0,
            }
        )
    areas = pd.DataFrame(rows)
    stops = pd.DataFrame(
        [
            {"stop_id": "T1", "stop_name": "Cork", "stop_lat": 51.9001, "stop_lon": -8.4701},
            {"stop_id": "T2", "stop_name": "Dublin", "stop_lat": 53.3501, "stop_lon": -6.2601},
        ]
    )
    return build_ireland_areas(areas=areas, stops=stops)


REQUIRED_TYPES = {
    "f1_gini": "lorenz_curve",
    "f2_disparity_ratio": "scatter_regression",
    "a3_walking_distance": "stacked_bar",
    "a4_coverage_equity": "lorenz_curve",
    "a7_investment_gap": "horizontal_bar",
    "c1_route_length": "horizontal_bar",
    "c2_stops_per_route": "box_violin",
    "c5_length_vs_frequency": "scatter_regression",
    "c7_network_topology": "horizontal_bar",
    "bsa2_operator_concentration": "gauge",
    "a5_service_deserts": "choropleth",
    "a6_urban_rural_gap": "scatter_regression",
    "c3_operator_hhi": "gauge",
    "d1_coverage_deprivation": "scatter_regression",
    "d7_deprivation_urban_rural": "heatmap",
    "b1_frequency": "box_violin",
    "b2_operating_hours": "stacked_bar",
    "b3_weekend_penalty": "stacked_bar",
    "ps5_scenario_comparison": "table",
    "bsa3_tier_distribution": "grouped_bar",
    "j2_bcr": "horizontal_bar",
    "j3_carbon": "horizontal_bar",
}


def test_catalogue_exhibits_distinct_and_omit_empty():
    extras = {
        "hhi": 896.0,
        "n_agencies": 4,
        "n_routes": 20,
        "mean_stops_per_route": 12.0,
        "stops_per_route": [4, 8, 12, 20, 30],
        "agencies": [
            {"name": "Dublin Bus", "n_routes": 10},
            {"name": "Bus Éireann", "n_routes": 6},
        ],
    }
    rows = precompute_ireland(_areas(), extras)
    national = [r for r in rows if r["region"] == "all" and r["urban_rural"] == "all"]
    by_id = {r["section_id"]: r for r in national}
    assert set(by_id) == set(CATALOGUE)

    for sid, expected in REQUIRED_TYPES.items():
        assert by_id[sid]["chart_data"].get("type") == expected, sid

    for sid, action in CATALOGUE.items():
        if action == OMIT or by_id[sid]["stats"].get("omit"):
            assert by_id[sid]["chart_data"] == {}
            assert by_id[sid]["stats"].get("omit") is True
            assert by_id[sid]["narrative"]

    # Lorenz has people in the title
    assert "people" in by_id["f1_gini"]["chart_data"]["title"].lower()
    # HHI is a gauge, not routes-per-agency bars
    assert by_id["c3_operator_hhi"]["chart_data"]["type"] != "horizontal_bar"
    # Access encodings are not three county bars
    access_types = {
        by_id[s]["chart_data"].get("type")
        for s in ("a3_walking_distance", "a5_service_deserts", "a6_urban_rural_gap")
    }
    assert "choropleth" in access_types
    assert access_types != {"horizontal_bar"}

    cork = next(r for r in rows if r["section_id"] == "a3_walking_distance" and r["region"] == "cork" and r["urban_rural"] == "all")
    dublin = next(r for r in rows if r["section_id"] == "a3_walking_distance" and r["region"] == "dublin" and r["urban_rural"] == "all")
    assert "Cork" in cork["narrative"]
    assert "Dublin" in dublin["narrative"]
    assert "Key finding" in cork["narrative"]
    assert "n_lsoas" not in cork["stats"]

    f1 = by_id["f1_gini"]
    if f1["stats"].get("palma") == 0:
        assert f1["stats"].get("palma_note")

    banned = ("BODS", "IMD", "LSOA", "TAG", "BSA", "DfT", "clone bars", "18 clone")
    for r in (cork, dublin, by_id["d7_deprivation_urban_rural"], by_id["d1_coverage_deprivation"]):
        text = r["narrative"]
        for word in banned:
            assert word not in text, word
        assert "Key finding" in text
        assert any(ch.isdigit() for ch in text)
        assert place_word(r) in text


def place_word(row):
    if row.get("region") == "cork":
        return "Cork"
    if row.get("region") == "dublin":
        return "Dublin"
    return "Republic"


def test_empty_filter_is_one_sentence():
    extras = {"hhi": 100.0}
    rows = precompute_ireland(_areas(), extras)
    empty = [r for r in rows if r["region"] == "dublin" and r["urban_rural"] == "rural"]
    # Dublin fixture is urban-only; rural Dublin should be empty.
    if empty:
        a3 = next(r for r in empty if r["section_id"] == "a3_walking_distance")
        assert a3["chart_data"] == {}
        assert "No Small Areas" in a3["narrative"]
