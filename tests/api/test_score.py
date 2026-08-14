"""Score API serialisation and compare labels stay English."""

from aequitas.analytics.score import compute_score


def test_score_payload_schema():
    payload = compute_score(
        {
            "pop_within_400m": 0.9,
            "evening_served": 0.8,
            "weekday_frequency": 0.6,
            "deprivation_service": 0.7,
        },
        n_areas=100,
        region="E12000005",
        urban_rural="urban",
    ).to_dict()
    assert set(payload) >= {"score", "components", "filter", "n_areas", "dropped", "formula"}
    assert payload["filter"] == {"region": "E12000005", "urban_rural": "urban"}
    assert payload["n_areas"] == 100
    assert isinstance(payload["score"], float)
    assert len(payload["components"]) == 4


def test_score_endpoint_on_client(api_client):
    resp = api_client.get("/api/score?region=all&urban_rural=all")
    assert resp.status_code == 200
    body = resp.json()
    assert "score" in body
    assert "components" in body
    assert "filter" in body
