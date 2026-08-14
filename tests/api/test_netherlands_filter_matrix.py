"""Every provincie × stedelijkheid × mode must have warehouse keys (or honest empty)."""

from pathlib import Path

import duckdb
import pytest

from aequitas.netherlands.constants import PROVINCE_NAME_BY_SLUG

WH = Path("data/aequitas_netherlands.duckdb")

REGIONS = ["all", *sorted(PROVINCE_NAME_BY_SLUG)]
URS = ("all", "urban", "rural")
MODES = ("bus", "all")


@pytest.mark.skipif(not WH.exists(), reason="NL warehouse not on disk")
def test_seventy_eight_filter_keys_exist() -> None:
    con = duckdb.connect(str(WH), read_only=True)
    keys = set(
        con.execute("SELECT region, urban_rural, mode FROM section_results GROUP BY 1,2,3").fetchall()
    )
    missing = []
    for region in REGIONS:
        for ur in URS:
            for mode in MODES:
                if (region, ur, mode) not in keys:
                    missing.append((region, ur, mode))
    assert not missing, f"missing warehouse keys: {missing[:12]}"


@pytest.mark.skipif(not WH.exists(), reason="NL warehouse not on disk")
def test_national_scores_differ_by_mode() -> None:
    import duckdb

    from aequitas.api.services.score import score_for_filter

    db = duckdb.connect(str(WH), read_only=True)
    bus = score_for_filter(db, "all", "all", mode="bus")
    all_pt = score_for_filter(db, "all", "all", mode="all")
    nh = score_for_filter(db, "noord-holland", "all", mode="bus")
    gr = score_for_filter(db, "groningen", "all", mode="bus")
    assert bus.score is not None and all_pt.score is not None
    assert abs(bus.score - all_pt.score) >= 0.5
    assert bus.n_areas == 13827
    assert nh.score is not None and gr.score is not None
    assert abs(nh.score - gr.score) > 0.5
