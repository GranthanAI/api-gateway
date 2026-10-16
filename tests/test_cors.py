import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import DEV_CORS_ORIGINS, settings
from app.middleware.cors import setup_cors


def _client(monkeypatch, environment: str, origins: str) -> TestClient:
    monkeypatch.setattr(settings, "ENVIRONMENT", environment)
    monkeypatch.setattr(settings, "CORS_ALLOW_ORIGINS", origins)
    app = FastAPI()
    setup_cors(app)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return TestClient(app)


def _preflight(client: TestClient, origin: str, method: str = "POST", headers: str = "authorization,content-type"):
    return client.options(
        "/ping",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers,
        },
    )


def test_dev_default_allows_localhost_dev_origin_with_credentials(monkeypatch):
    client = _client(monkeypatch, "development", "")
    r = _preflight(client, DEV_CORS_ORIGINS[2])
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == DEV_CORS_ORIGINS[2]
    assert r.headers["access-control-allow-credentials"] == "true"


def test_dev_default_rejects_unlisted_origin(monkeypatch):
    client = _client(monkeypatch, "development", "")
    r = _preflight(client, "https://evil.example")
    assert "access-control-allow-origin" not in r.headers


def test_production_with_no_origins_allows_no_cross_origin(monkeypatch):
    client = _client(monkeypatch, "production", "")
    r = _preflight(client, "http://localhost:5173")
    assert "access-control-allow-origin" not in r.headers


def test_production_explicit_origin_allowed_others_rejected(monkeypatch):
    client = _client(monkeypatch, "production", "https://app.granthan.example")
    assert _preflight(client, "https://app.granthan.example").headers["access-control-allow-origin"] == "https://app.granthan.example"
    assert "access-control-allow-origin" not in _preflight(client, "https://other.example").headers


def test_production_wildcard_is_refused(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "CORS_ALLOW_ORIGINS", "*")
    with pytest.raises(ValueError):
        setup_cors(FastAPI())


def test_wildcard_in_dev_never_enables_credentials(monkeypatch):
    client = _client(monkeypatch, "development", "*")
    r = _preflight(client, "https://anything.example")
    assert r.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in r.headers


def test_disallowed_header_and_method_are_rejected(monkeypatch):
    client = _client(monkeypatch, "production", "https://app.granthan.example")
    assert _preflight(client, "https://app.granthan.example", headers="x-internal-token").status_code == 400
    assert _preflight(client, "https://app.granthan.example", method="TRACE").status_code == 400


def test_idempotency_header_is_allowed(monkeypatch):
    client = _client(monkeypatch, "production", "https://app.granthan.example")
    assert _preflight(client, "https://app.granthan.example", headers="x-idempotency-key,authorization").status_code == 200
