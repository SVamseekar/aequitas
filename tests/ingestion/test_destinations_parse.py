"""Parsers for official dest extracts — fixtures only, no live HTTP."""

import json

import pandas as pd

from aequitas.ingestion.destinations import (
    bpe_points,
    catalog_file_urls,
    nabijheid_distances,
)


def test_catalog_file_urls_ckan_and_datagouv() -> None:
    ckan = {
        "result": {
            "results": [
                {
                    "resources": [
                        {"format": "CSV", "url": "https://example.gov/schools.csv"},
                        {"format": "HTML", "url": "https://example.gov/page"},
                    ]
                }
            ]
        }
    }
    gouv = {
        "resources": [
            {
                "format": "zip",
                "url": "https://www.data.gouv.fr/fr/datasets/r/abc",
                "title": "BPE 2023",
            }
        ]
    }
    cbs = {
        "value": [
            {"name": "TypedDataSet", "url": "https://opendata.cbs.nl/ODataApi/odata/84718NED/TypedDataSet"},
            {"name": "TableInfos", "url": "https://opendata.cbs.nl/ODataApi/odata/84718NED/TableInfos"},
        ]
    }
    assert catalog_file_urls(ckan) == ["https://example.gov/schools.csv"]
    ckan_cubes = {
        "result": {
            "results": [
                {
                    "resources": [
                        {
                            "format": "CSV",
                            "url": "https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/HSPAO19/CSV/1.0/en",
                        }
                    ]
                }
            ]
        }
    }
    assert catalog_file_urls(ckan_cubes) == []
    assert catalog_file_urls(gouv) == ["https://www.data.gouv.fr/fr/datasets/r/abc"]
    assert catalog_file_urls(cbs) == ["https://opendata.cbs.nl/ODataApi/odata/84718NED/TypedDataSet"]


def test_nabijheid_distances_maps_official_km() -> None:
    raw = pd.DataFrame(
        {
            "WijkenEnBuurten": ["BU03630000", "GM0363"],
            "AfstandTotHuisartsenpraktijk_5": [0.8, 1.2],
            "AfstandTotZiekenhuis_11": [3.4, 4.1],
            "AfstandTotSchool_21": [0.4, 0.9],
        }
    )
    out = nabijheid_distances(raw)
    assert list(out["buurt_code"]) == ["BU03630000"]
    assert float(out.loc[0, "km_gp"]) == 0.8
    assert float(out.loc[0, "km_hospital"]) == 3.4
    assert float(out.loc[0, "km_school"]) == 0.4


def test_bpe_points_splits_gp_and_school() -> None:
    raw = pd.DataFrame(
        {
            "LAMBERT_X": [650000.0, 651000.0, 652000.0],
            "LAMBERT_Y": [6860000.0, 6861000.0, 6862000.0],
            "TYPEQU": ["A504", "D201", "A108"],
            "AN": ["001", "002", "003"],
            "DEPCOM": ["75056", "69001", "13001"],
        }
    )
    frames = bpe_points(raw)
    assert "gp" in frames and "school" in frames
    assert len(frames["gp"]) == 1
    assert len(frames["school"]) == 1
    assert frames["gp"]["dest_type"].iloc[0] == "gp"
    assert frames["school"]["dest_type"].iloc[0] == "school"
    assert "lsoa" not in frames["gp"].columns
