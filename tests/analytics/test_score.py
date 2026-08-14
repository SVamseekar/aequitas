"""Quoteable in-country score — fixture, renormalise, London rural."""

from aequitas.analytics.score import compute_score, terms_from_section_stats


def test_known_fixture_exact_score():
    result = compute_score(
        {
            "pop_within_400m": 1.0,
            "evening_served": 1.0,
            "weekday_frequency": 1.0,
            "deprivation_service": 1.0,
        }
    )
    assert result.score == 100.0


def test_weighted_fixture():
    # 0.40*0.5 + 0.25*0.8 + 0.20*0.5 + 0.15*0.0 = 0.20+0.20+0.10+0 = 0.50 → 50
    result = compute_score(
        {
            "pop_within_400m": 0.5,
            "evening_served": 0.8,
            "weekday_frequency": 0.5,
            "deprivation_service": 0.0,
        }
    )
    assert result.score is not None
    assert round(result.score, 1) == 50.0


def test_missing_component_renormalises():
    result = compute_score(
        {
            "pop_within_400m": 1.0,
            "evening_served": None,
            "weekday_frequency": 1.0,
            "deprivation_service": 1.0,
        }
    )
    assert result.score == 100.0
    assert "evening_served" in result.dropped
    evening = next(c for c in result.components if c.id == "evening_served")
    assert evening.missing is True
    assert result.note is not None
    assert "not in this cut" in result.note


def test_london_rural_null_not_nan():
    result = compute_score({}, region="E12000007", urban_rural="rural")
    assert result.score is None
    assert result.note is not None
    assert "London" in result.note
    dumped = result.to_dict()
    assert dumped["score"] is None


def test_terms_from_stats_do_not_invent_national():
    terms, n = terms_from_section_stats(
        {"pct_covered": 80.0, "n_lsoas": 10},
        None,
        {"national_avg": 50},
        {"r": -0.2},
    )
    assert terms["pop_within_400m"] == 0.8
    assert terms["evening_served"] is None
    assert terms["weekday_frequency"] == 0.5
    assert abs(terms["deprivation_service"] - 0.8) < 1e-9
    assert n == 10


def test_regional_frequency_uses_value_not_national_avg():
    terms, _ = terms_from_section_stats(
        {"pct_covered": 78.6},
        {"pct_evening_isolated": 11.8},
        {"value": 66.4, "national_avg": 65.42},
        {"r": -0.08},
    )
    assert abs(terms["weekday_frequency"] - 0.664) < 1e-9
