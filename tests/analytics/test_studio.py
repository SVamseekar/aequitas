"""Studio patch validation and walk-to-stop (no PBF)."""

import pandas as pd
import pytest

from aequitas.analytics.score import compute_score
from aequitas.analytics.studio import (
    WALK_LABEL,
    apply_studio,
    parse_studio_patch,
    parse_upload_text,
    walk_to_stop_delta,
)


def test_patch_validation_requires_ops():
    patch, err = parse_studio_patch({"country": "england", "ops": []})
    assert patch is None
    assert err and "at least one" in err.lower()


def test_patch_rejects_england_click_on_ireland():
    patch, err = parse_studio_patch(
        {
            "country": "ireland",
            "region": "cork",
            "urban_rural": "all",
            "ops": [{"op": "add_stop", "lat": 52.483, "lon": -1.9, "name": "Birmingham"}],
        }
    )
    assert patch is None
    assert err and "Republic" in err


def test_patch_accepts_cork_click_on_ireland():
    patch, err = parse_studio_patch(
        {
            "country": "ireland",
            "ops": [{"op": "add_stop", "lat": 51.9, "lon": -8.47, "name": "Cork"}],
        }
    )
    assert err is None
    assert patch is not None


def test_patch_rejects_point_outside_england():
    patch, err = parse_studio_patch(
        {
            "country": "england",
            "region": "all",
            "urban_rural": "all",
            "ops": [{"op": "add_stop", "lat": 48.8, "lon": 2.3, "name": "Paris"}],
        }
    )
    assert patch is None
    assert err and "outside England" in err


def test_patch_accepts_add_stop_in_england():
    patch, err = parse_studio_patch(
        {
            "country": "england",
            "region": "E12000005",
            "urban_rural": "all",
            "source": "drawn",
            "ops": [{"op": "add_stop", "lat": 52.48, "lon": -1.9, "name": "Birmingham"}],
        }
    )
    assert err is None
    assert patch is not None
    assert patch.ops[0].op == "add_stop"


def test_frequency_needs_factor():
    _, err = parse_studio_patch(
        {"country": "england", "ops": [{"op": "frequency_uplift"}]}
    )
    assert err and "factor" in err.lower()


def test_csv_upload_two_rows():
    text = "lat,lon,name\n52.5,-1.9,A\n52.51,-1.91,B\n"
    ops, err = parse_upload_text(text, filename="stops.csv")
    assert err is None
    assert len(ops) == 2
    assert ops[0].op == "add_stop"


def test_walk_to_stop_two_centroids_one_stop():
    centroids = pd.DataFrame(
        [
            {"area": "E01000001", "lat": 52.5, "lon": -1.9, "pop": 1000, "imd_decile": 1},
            {"area": "E01000002", "lat": 53.8, "lon": -1.5, "pop": 800, "imd_decile": 8},
        ]
    )
    # Stop sits on the first centroid only (~0 m).
    after = walk_to_stop_delta(centroids, [], [(52.5, -1.9)], region="all", urban_rural="all")
    assert after["people_gained"] == 1000
    assert after["people_lost"] == 0
    assert after["score_before"] is not None
    assert after["score_after"] is not None
    assert after["score_after"] > after["score_before"]
    # Score uses only the 400 m term — same function as Wave 2.
    only_400 = compute_score({"pop_within_400m": after["share_after"]}, n_areas=2)
    assert after["score_after"] == pytest.approx(only_400.score)
    assert after["deciles"][0]["imd_decile"] == 1


def test_score_before_after_when_only_400m_changes():
    centroids = pd.DataFrame(
        [{"area": "A", "lat": 52.5, "lon": -1.9, "pop": 500, "imd_decile": 3}]
    )
    terms = {
        "pop_within_400m": 0.0,
        "evening_served": 0.8,
        "weekday_frequency": 0.6,
        "deprivation_service": 0.7,
    }
    before_stops: list[tuple[float, float]] = []
    after_stops = [(52.5, -1.9)]
    out = walk_to_stop_delta(
        centroids, before_stops, after_stops, region="E12000005", urban_rural="all", other_terms=terms
    )
    expected_before = compute_score({**terms, "pop_within_400m": 0.0}, n_areas=1, region="E12000005")
    expected_after = compute_score({**terms, "pop_within_400m": 1.0}, n_areas=1, region="E12000005")
    assert out["score_before"] == pytest.approx(expected_before.score)
    assert out["score_after"] == pytest.approx(expected_after.score)


def test_apply_studio_labels_walk_to_stop():
    centroids = pd.DataFrame(
        [{"area": "A", "lat": 52.5, "lon": -1.9, "pop": 100, "imd_decile": 2}]
    )
    patch, err = parse_studio_patch(
        {
            "country": "england",
            "region": "all",
            "urban_rural": "all",
            "ops": [{"op": "add_stop", "lat": 52.5, "lon": -1.9}],
        }
    )
    assert err is None and patch
    result = apply_studio(patch, centroids=centroids, baseline_stops=[])
    assert result.ok
    assert "walk-to-stop" in result.note
    assert WALK_LABEL.split(",")[0] in result.note
    assert "45-minute" in result.note


def test_frequency_without_r5py_is_honest(tmp_path):
    centroids = pd.DataFrame(
        [{"area": "A", "lat": 52.5, "lon": -1.9, "pop": 100, "imd_decile": 2}]
    )
    patch, _ = parse_studio_patch(
        {
            "country": "england",
            "ops": [{"op": "frequency_uplift", "factor": 1.5}],
        }
    )
    assert patch
    result = apply_studio(
        patch,
        centroids=centroids,
        baseline_stops=[],
        raw_dir=tmp_path,
        processed_dir=tmp_path,
    )
    assert result.needs_r5py
    assert "r5py" in result.note.lower()
    assert "1.1" not in result.note


def test_apply_empty_centroids_is_honest():
    patch, _ = parse_studio_patch(
        {"country": "england", "ops": [{"op": "add_stop", "lat": 52.5, "lon": -1.9}]}
    )
    assert patch
    result = apply_studio(patch, centroids=pd.DataFrame(), baseline_stops=[])
    assert result.mode == "needs_centroids"
    assert result.people_gained == 0
    assert result.score_before == result.score_after


def test_region_filter_does_not_credit_other_itl1():
    from aequitas.analytics.centroids import filter_centroids_for_studio

    demo = pd.DataFrame(
        [
            {
                "lsoa_cd": "E010WM001",
                "lsoa_nm": "WM rural 1",
                "population": 900,
                "imd_decile": 4,
                "region": "West Midlands",
                "urban_rural": "Rural",
            },
            {
                "lsoa_cd": "E010YK001",
                "lsoa_nm": "York 1",
                "population": 800,
                "imd_decile": 6,
                "region": "Yorkshire and The Humber",
                "urban_rural": "Rural",
            },
        ]
    )
    pts = pd.DataFrame(
        [
            {"lsoa_code": "E010WM001", "lat": 52.4, "lon": -2.3},
            {"lsoa_code": "E010YK001", "lat": 54.0, "lon": -1.1},
        ]
    )
    wm = filter_centroids_for_studio(demo, pts, region="E12000005", urban_rural="rural")
    assert list(wm["area"]) == ["E010WM001"]
    out = walk_to_stop_delta(wm, [], [(54.0, -1.1)], region="E12000005", urban_rural="rural")
    assert out["people_gained"] == 0


def test_uncovered_centroid_fixture_moves_score_and_people():
    """Tiny real-shaped frame (also tests/fixtures/studio_centroids.parquet)."""
    from pathlib import Path

    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "studio_centroids.parquet"
    pts = pd.read_parquet(fixture)
    assert len(pts) >= 5
    centroids = pd.DataFrame(
        [
            {"area": "E01000011", "name": "Desert A", "lat": 52.35, "lon": -2.45, "pop": 1200, "imd_decile": 2},
            {"area": "E01000012", "name": "Covered B", "lat": 52.48, "lon": -1.90, "pop": 800, "imd_decile": 7},
            {"area": "E01000013", "name": "Far C", "lat": 52.20, "lon": -2.70, "pop": 400, "imd_decile": 3},
            {"area": "E01000014", "name": "Near D", "lat": 52.351, "lon": -2.449, "pop": 350, "imd_decile": 2},
            {"area": "E01000015", "name": "East E", "lat": 52.55, "lon": -1.70, "pop": 500, "imd_decile": 8},
        ]
    )
    # Existing stop covers only B (~0 m).
    baseline = [(52.48, -1.90)]
    patch, err = parse_studio_patch(
        {
            "country": "england",
            "region": "E12000005",
            "urban_rural": "rural",
            "ops": [{"op": "add_stop", "lat": 52.35, "lon": -2.45, "name": "New desert stop"}],
        }
    )
    assert err is None and patch
    terms = {"evening_served": 0.5, "weekday_frequency": 0.4, "deprivation_service": 0.6}
    result = apply_studio(patch, centroids=centroids, baseline_stops=baseline, other_terms=terms)
    assert result.mode == "walk_to_stop"
    assert result.people_gained > 0
    assert result.score_after is not None and result.score_before is not None
    assert result.score_after > result.score_before
    assert any(d["people_gained"] > 0 for d in result.deciles)


def test_ireland_studio_empty_centroids_is_honest():
    patch, _ = parse_studio_patch(
        {"country": "ireland", "ops": [{"op": "add_stop", "lat": 53.3, "lon": -6.2}]}
    )
    assert patch
    result = apply_studio(patch, centroids=pd.DataFrame())
    assert result.mode == "needs_centroids"
    assert "centroid" in result.note.lower() or "walk-to-stop" in result.note.lower()
