"""Tests for ApiConfig's new tenancy/auth env fields."""
from aequitas.api.config import ApiConfig


def test_database_url_defaults_to_local_dev(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    cfg = ApiConfig()
    assert cfg.database_url == "postgresql://localhost/aequitas"


def test_database_url_reads_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example.com/aequitas_prod")
    cfg = ApiConfig()
    assert cfg.database_url == "postgresql://example.com/aequitas_prod"


def test_session_secret_reads_env(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret-value")
    cfg = ApiConfig()
    assert cfg.session_secret == "test-secret-value"


def test_google_client_id_and_secret_read_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id-123")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret-456")
    cfg = ApiConfig()
    assert cfg.google_client_id == "client-id-123"
    assert cfg.google_client_secret == "client-secret-456"


def test_brevo_api_key_reads_env(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "brevo-key-789")
    cfg = ApiConfig()
    assert cfg.brevo_api_key == "brevo-key-789"


def test_supabase_jwt_secret_removed():
    cfg = ApiConfig()
    assert not hasattr(cfg, "supabase_jwt_secret")
