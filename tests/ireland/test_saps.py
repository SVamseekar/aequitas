from pathlib import Path

import pandas as pd

from aequitas.ireland.saps import attach_saps_theme_shares
from aequitas.ireland.sections import CATALOGUE, OMIT, REPLACE, SAME, catalogue_counts


def test_catalogue_after_saps_recheck():
    c = catalogue_counts()
    assert c["same"] == 36
    assert c["replace"] == 12
    assert c["omit"] == 7
    assert c["answers"] == 55
    assert CATALOGUE["d2_coverage_unemployment"] == SAME
    assert CATALOGUE["d3_coverage_car"] == SAME
    assert CATALOGUE["d4_coverage_elderly"] == SAME
    assert CATALOGUE["d5_coverage_income"] == OMIT
    assert CATALOGUE["j2_bcr"] == REPLACE


def test_attach_saps_theme_shares_from_disk():
    path = Path("data/raw/ireland/saps_2022.csv")
    if not path.exists():
        return
    areas = pd.DataFrame({"sa_code": ["missing"]})
    # use one real GUID from the file
    head = pd.read_csv(path, usecols=["GUID"], nrows=3)
    areas = pd.DataFrame({"sa_code": head["GUID"].astype(str).tolist()})
    out = attach_saps_theme_shares(areas, path)
    assert out["unemp_rate"].notna().any()
    assert out["no_car_share"].notna().any()
    assert out["elderly_share"].notna().any()
    assert (out["unemp_rate"] <= 1).all()
