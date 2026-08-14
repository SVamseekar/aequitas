"""NL writers: 78 filters, Sunday from calendar_dates, no invented SES deciles."""

from __future__ import annotations

import pandas as pd

from aequitas.netherlands.constants import PROVINCE_NAME_BY_SLUG
from aequitas.netherlands.process import ses_decile_from_score
from aequitas.netherlands.sections import CATALOGUE, precompute_netherlands


def _toy_areas() -> pd.DataFrame:
    slugs = list(PROVINCE_NAME_BY_SLUG)
    rows = []
    i = 0
    for slug in slugs:
        for ur, sted in (("urban", 2), ("rural", 5)):
            for _ in range(4):
                i += 1
                ses = None if i % 4 == 0 else float((i % 10) - 5)
                rows.append(
                    {
                        "buurt_code": f"BU{i:08d}",
                        "name": f"b{i}",
                        "lat": 52.0,
                        "lon": 5.0,
                        "population": 1000 + i,
                        "region": slug,
                        "urban_rural": ur,
                        "stedelijkheid": sted,
                        "ses_score": ses,
                        "ses_decile": None,
                        "within_400m": i % 3 != 0,
                        "sqi": 40.0 + (i % 20),
                        "stop_count": 2,
                        "weekday_trips": 10,
                        "evening_isolated": i % 5 == 0,
                        "sunday_desert": i % 7 == 0,
                        "sunday_trips": 0 if i % 7 == 0 else 3,
                        "trips_per_capita": 0.1,
                        "stops_per_1k": 1.5,
                        "area_km2": 2.0,
                    }
                )
    df = pd.DataFrame(rows)
    df["ses_decile"] = ses_decile_from_score(df["ses_score"])
    return df


def test_ses_decile_leaves_nulls() -> None:
    s = pd.Series([0.1, None, 0.4, 0.2, None, 0.9, 0.3, 0.5, 0.6, 0.7, 0.8, -0.2])
    d = ses_decile_from_score(s)
    assert d.isna().sum() == 2
    assert d.notna().sum() == 10


def test_precompute_covers_provincie_stedelijkheid() -> None:
    extras = {"mode": "bus", "hhi": 1333.0, "n_agencies": 26, "n_routes": 3047, "agencies": [], "stops_per_route": [5, 10, 20]}
    rows = precompute_netherlands(_toy_areas(), extras)
    keys = {(r["region"], r["urban_rural"]) for r in rows}
    assert ("all", "all") in keys
    assert ("all", "rural") in keys
    assert ("groningen", "rural") in keys
    assert ("noord-holland", "urban") in keys
    assert ("unknown", "all") not in keys
    assert len(keys) == 13 * 3
    assert sum(1 for r in rows if r["region"] == "all" and r["urban_rural"] == "all") == len(CATALOGUE)
    d7 = next(r for r in rows if r["section_id"] == "d7_deprivation_urban_rural" and r["region"] == "all" and r["urban_rural"] == "all")
    z = d7["chart_data"].get("z") or d7["chart_data"].get("values")
    assert z
    flat = [c for row in z for c in row if c is not None]
    assert any(v != 0 for v in flat)
    b1 = next(r for r in rows if r["section_id"] == "b1_frequency" and r["region"] == "all" and r["urban_rural"] == "all")
    assert b1["chart_data"]["type"] == "horizontal_bar"
    assert len(b1["chart_data"]["data"]) >= 10
    b3 = next(r for r in rows if r["section_id"] == "b3_weekend_penalty" and r["region"] == "all")
    assert b3["stats"]["pct_sunday_desert"] < 100
    omit = next(r for r in rows if r["section_id"] == "d9c_crime_access")
    assert omit["stats"].get("omit")
    c3 = next(
        r
        for r in rows
        if r["section_id"] == "c3_operator_hhi" and r["region"] == "all" and r["urban_rural"] == "all"
    )
    assert c3["chart_data"]["markers"]
    assert c3["chart_data"]["bands"][0].get("color_hint")


def test_b1_drops_unknown_region_bar() -> None:
    areas = _toy_areas()
    extra = areas.iloc[:3].copy()
    extra["region"] = "unknown"
    extra["sqi"] = 27.6
    extras = {"mode": "bus", "hhi": 1333.0, "n_agencies": 26, "n_routes": 3047, "agencies": [], "stops_per_route": [5]}
    rows = precompute_netherlands(pd.concat([areas, extra], ignore_index=True), extras)
    b1 = next(r for r in rows if r["section_id"] == "b1_frequency" and r["region"] == "all" and r["urban_rural"] == "all")
    labels = [d["label"] for d in b1["chart_data"]["data"]]
    assert "Unknown" not in labels
    assert "unknown" not in {str(x).lower() for x in labels}
    assert len(labels) == 12
    assert b1["stats"]["n_excluded_no_provincie"] == 3
    assert "3" in (b1["chart_data"].get("note") or "")


def test_c1_c2_honest_empty_when_spr_skipped() -> None:
    extras = {"mode": "bus", "hhi": 1333.0, "n_agencies": 26, "n_routes": 3047, "agencies": [], "stops_per_route": []}
    rows = precompute_netherlands(_toy_areas(), extras)
    c1 = next(
        r
        for r in rows
        if r["section_id"] == "c1_route_length" and r["region"] == "all" and r["urban_rural"] == "all"
    )
    c2 = next(
        r
        for r in rows
        if r["section_id"] == "c2_stops_per_route" and r["region"] == "all" and r["urban_rural"] == "all"
    )
    assert c1["chart_data"].get("empty_reason") == "Stops-per-route list not persisted"
    assert c1["chart_data"].get("data") == []
    assert c2["chart_data"].get("empty_reason") == "Stops-per-route list not persisted"
    assert "not persisted" in (c1["narrative"] or "").lower()
