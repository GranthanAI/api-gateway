"""P3a: public paths are matched exactly on a normalised path; lookalikes must authenticate."""

import asyncio

import pytest

from app.gateway.paths import is_public_path, normalize_path
from tests.conftest import asgi_status

REAL_PUBLIC = [
    "/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/refresh", "/api/v1/auth/verify-email",
    "/api/v1/auth/resend-verification", "/api/v1/auth/forgot-password", "/api/v1/auth/reset-password",
    "/api/v1/live", "/api/v1/ready", "/api/v1/info", "/api/v1/auth/health", "/api/v1/memory/health",
    "/api/v1/conversations/health", "/api/v1/graph/health", "/api/v1/llm/health",
    "/health", "/openapi.json", "/docs", "/docs/", "/docs/oauth2-redirect", "/redoc", "/api/v1/auth/login/",
    "/api/v1//auth//login",
]

MUST_AUTHENTICATE = [
    "/api/v1/files/health", "/api/v1/conversations/x/info", "/api/v1/auth/login/../../conversations",
    "/api/v1/memory/facts", "/api/v1//health/../files", "/api/v1/auth/login/%2e%2e/%2e%2e/conversations",
    "/api/v1/auth/login/%2E%2E/files", "/api/v1/auth%2Flogin/../files", "/api/v1/files%2Fhealth",
    "/api/v1/docs/../files", "/api/v1/documents", "/api/v1/docsx", "/api/v1/redoc2", "/api/v1/files/docs",
    "/api/v1/conversations/openapi.json", "/api/v1/auth/login-anything", "/api/v1/auth/loginx",
    "/api/v1/files/live", "/api/v1/./health", "/api/v1/auth\login", "/api/v1/user/info",
]


@pytest.mark.parametrize("path", REAL_PUBLIC)
def test_real_public_paths_stay_public(path):
    assert is_public_path(path)


@pytest.mark.parametrize("path", MUST_AUTHENTICATE)
def test_lookalike_and_traversal_paths_are_not_public(path):
    assert not is_public_path(path)


def test_normalisation():
    assert normalize_path("/api/v1//Health/") == "/health"
    assert normalize_path("/api/v1") == "/"
    assert normalize_path("/api/v1x/health") == "/api/v1x/health"
    assert normalize_path("/a/../b") is None and normalize_path("/a/%2e%2E/b") is None


@pytest.mark.parametrize("path", MUST_AUTHENTICATE)
def test_gateway_answers_401_without_a_token(path):
    assert asyncio.run(asgi_status(path)) == 401


def test_query_string_cannot_make_a_path_public():
    assert asyncio.run(asgi_status("/api/v1/memory/facts", query=b"x=/health")) == 401


@pytest.mark.parametrize("path", ["/api/v1/live", "/api/v1/ready"])
def test_real_public_paths_skip_authentication(path):
    assert asyncio.run(asgi_status(path)) == 200


def test_billing_health_probe_is_public_but_only_at_the_exact_path():
    assert is_public_path("/api/v1/billing/health")
    assert is_public_path("/api/v1/billing/health/")
    for p in ("/api/v1/billing/healthx", "/api/v1/billing/health/x", "/api/v1/files/billing/health",
              "/api/v1/billing/me/health", "/api/v1/billing/health/../me"):
        assert not is_public_path(p), p
