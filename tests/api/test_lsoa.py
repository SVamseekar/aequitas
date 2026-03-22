def test_lsoa_invalid_table(api_client):
    resp = api_client.get("/api/lsoa/evil_table")
    assert resp.status_code == 400
