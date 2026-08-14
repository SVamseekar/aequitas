"""Netherlands catalogue — 55 answers re-derived from CBS, not copied Ireland omits."""

from aequitas.intelligence.section_registry import SECTION_REGISTRY
from aequitas.netherlands.sections import CATALOGUE, OMIT, REPLACE, SAME, catalogue_counts


def test_fifty_five_answers() -> None:
    assert len(CATALOGUE) == 55
    assert set(CATALOGUE) == set(SECTION_REGISTRY)
    counts = catalogue_counts()
    assert counts["answers"] == 55
    assert counts["same"] + counts["replace"] + counts["omit"] == 55


def test_cbs_variables_not_copied_ireland_omits() -> None:
    # CBS Kerncijfers 85984NED publishes these; Ireland omitted some of them.
    assert CATALOGUE["d2_coverage_unemployment"] == SAME
    assert CATALOGUE["d3_coverage_car"] == SAME
    assert CATALOGUE["d4_coverage_elderly"] == SAME
    assert CATALOGUE["d5_coverage_income"] == SAME
    assert CATALOGUE["f3_ethnic_access"] == SAME
    assert CATALOGUE["d9c_crime_access"] == OMIT
    assert CATALOGUE["j2_bcr"] == REPLACE
    assert CATALOGUE["bsa1_franchising_readiness"] == REPLACE
