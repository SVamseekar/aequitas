"""Exact band assignment from known inputs."""

import pandas as pd

from aequitas.analytics.bands import (
    assign_service_band,
    assign_travel_band,
    filter_bands,
    hansen_from_minutes,
    summarise_bands,
)


def test_service_band_no_stop():
    band, why = assign_service_band(stop_count=0, no_service=False, sqi=90)
    assert band == 1
    assert "400" in why or "No stop" in why


def test_service_band_evening_sunday():
    band, why = assign_service_band(
        stop_count=2, no_service=False, evening_isolated=True, sunday_desert=True, sqi=80
    )
    assert band == 2
    assert "evening" in why.lower()


def test_service_band_sqi_thresholds():
    assert assign_service_band(stop_count=1, sqi=10)[0] == 3
    assert assign_service_band(stop_count=1, sqi=40)[0] == 4
    assert assign_service_band(stop_count=1, sqi=60)[0] == 5
    assert assign_service_band(stop_count=1, sqi=80)[0] == 6


def test_travel_band_from_counts_not_hansen():
    assert assign_travel_band(t_15=0, t_30=0, t_45=0)[0] == 1
    assert assign_travel_band(t_15=0, t_30=0, t_45=4)[0] == 2
    assert assign_travel_band(t_15=1, t_30=5, t_45=8)[0] == 3
    assert assign_travel_band(t_15=8, t_30=20, t_45=40)[0] == 4
    assert assign_travel_band(t_15=10, t_30=80, t_45=100)[0] == 5
    assert assign_travel_band(t_15=30, t_30=80, t_45=100)[0] == 6


def test_hansen_only_from_minutes():
    minutes = pd.Series([10.0, 20.0, 40.0])
    h = hansen_from_minutes(minutes, beta=0.05)
    assert h > 0
    # Counts must not be passed off as Hansen in the summary.
    df = pd.DataFrame(
        {
            "lsoa": ["E1"],
            "band": [4],
            "scheme": ["service"],
            "why": ["x"],
            "population": [100],
            "imd_decile": [3],
            "region_code": ["E12000005"],
            "region": ["West Midlands"],
            "urban_rural_norm": ["rural"],
            "stop_count": [1],
        }
    )
    payload = summarise_bands(df, region="E12000005", urban_rural="rural")
    assert payload["hansen_available"] is False
    assert "minutes" in payload["hansen_note"]


def test_filter_empty_is_empty_payload():
    df = pd.DataFrame(
        {
            "lsoa": ["E1"],
            "band": [3],
            "scheme": ["service"],
            "why": ["thin"],
            "population": [100],
            "imd_decile": [2],
            "region_code": ["E12000005"],
            "region": ["West Midlands"],
            "urban_rural_norm": ["urban"],
            "stop_count": [1],
        }
    )
    empty = summarise_bands(df, region="E12000005", urban_rural="rural")
    assert empty["empty"] is True
    assert empty["n_areas"] == 0
    london = summarise_bands(df, region="E12000007", urban_rural="rural")
    assert london["empty"] is True
    assert "London" in london["empty_reason"]


def test_filter_bands_region():
    df = pd.DataFrame(
        {
            "lsoa": ["A", "B"],
            "region_code": ["E12000005", "E12000002"],
            "urban_rural_norm": ["rural", "rural"],
        }
    )
    out = filter_bands(df, region="E12000005", urban_rural="rural")
    assert list(out["lsoa"]) == ["A"]


def _band_rows(**overrides):
    base = {
        "lsoa": ["A", "B", "C"],
        "band": [1, 6, 6],
        "scheme": ["service"] * 3,
        "why": ["no stop", "high", "high"],
        "population": [100, 100, 50],
        "imd_decile": [1, 5, 5],
        "region_code": ["E12000005", "E12000005", "Unknown"],
        "region": ["West Midlands", "West Midlands", "Unknown"],
        "lad_cd": ["E06000051", "E06000051", "E09000004"],
        "lad_nm": ["Shropshire", "Shropshire", "Bexley"],
        "urban_rural_norm": ["rural", "rural", "urban"],
        "stop_count": [0, 2, 1],
    }
    base.update(overrides)
    return pd.DataFrame(base)


def test_national_map_is_share_in_worst_two_not_modal_six():
    df = _band_rows()
    payload = summarise_bands(df, region="all", urban_rural="all")
    assert payload["map"]["color_mode"] == "continuous"
    assert "1–2" in payload["map"]["metric_label"] or "1-2" in payload["map"]["metric_label"]
    codes = {r["area_code"]: r for r in payload["map"]["data"]}
    assert "Unknown" not in codes
    assert codes["E12000005"]["value"] == 50.0
    assert payload["unmatched_people"] == 50
    assert "unmatched" in (payload.get("unmatched_note") or "").lower()


def test_unknown_region_filled_from_same_lad():
    df = pd.DataFrame(
        {
            "lsoa": ["A", "B"],
            "band": [4, 4],
            "scheme": ["service", "service"],
            "why": ["m", "m"],
            "population": [10, 20],
            "imd_decile": [3, 3],
            "region_code": ["E12000009", "Unknown"],
            "region": ["South West", "Unknown"],
            "lad_cd": ["E06000052", "E06000052"],
            "lad_nm": ["Cornwall", "Cornwall"],
            "urban_rural_norm": ["rural", "rural"],
            "stop_count": [1, 1],
        }
    )
    payload = summarise_bands(df, region="all", urban_rural="all")
    codes = [r["area_code"] for r in payload["map"]["data"]]
    assert codes == ["E12000009"]
    assert payload["unmatched_people"] == 0
    assert payload["people"] == 30
