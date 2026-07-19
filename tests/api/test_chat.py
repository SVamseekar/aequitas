def test_chat_without_faiss_returns_503(api_client):
    """When FAISS index is not loaded, chat returns 503."""
    resp = api_client.post("/api/chat", json={"query": "What is the Gini?"})
    assert resp.status_code == 503
    assert "unavailable" in resp.json()["detail"].lower()


def test_chat_request_uses_query_field(api_client):
    """Body field is `query` — wrong shapes should 422, not silent misuse."""
    resp = api_client.post("/api/chat", json={"message": "What is the Gini?"})
    assert resp.status_code == 422
