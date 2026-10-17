import time

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.gateway.router import gateway_router
from app.main import app


def test_tools_path_routes_to_the_llm_service_registry_endpoint():
    assert gateway_router.route_request("/api/v1/tools") == ("llm", "/api/v1/tools")


@pytest.mark.parametrize("path", ["/api/v1/tools/", "/api/v1/tools/web_search", "/api/v1/toolsmith", "/api/v1/tools/../internal/x"])
def test_no_subpaths_or_lookalikes_are_routed(path):
    assert gateway_router.route_request(path) is None


def _token():
    return jwt.encode({"sub": "user-1", "exp": int(time.time()) + 600}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _client(handler):
    app.state.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TestClient(app)  # no lifespan: the mock client above stands in for the real pool


def test_authenticated_get_is_proxied_to_the_llm_service_with_the_user_id():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["user"] = str(request.url), request.headers.get("x-user-id")
        return httpx.Response(200, json={"tools": [{"id": "web_search"}], "max_selected": 5})

    r = _client(handler).get("/api/v1/tools", headers={"Authorization": f"Bearer {_token()}"})
    assert r.status_code == 200 and r.json()["tools"][0]["id"] == "web_search"
    assert seen["url"].endswith("/api/v1/tools") and seen["user"] == "user-1"


def test_unauthenticated_requests_are_rejected_before_reaching_the_llm_service():
    def handler(request):  # pragma: no cover - must not be called
        raise AssertionError("upstream reached without authentication")

    c = _client(handler)
    assert c.get("/api/v1/tools").status_code == 401
    assert c.get("/api/v1/tools", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_only_get_is_allowed(method):
    def handler(request):  # pragma: no cover
        raise AssertionError("write method reached the LLM service")

    r = getattr(_client(handler), method)("/api/v1/tools", headers={"Authorization": f"Bearer {_token()}"})
    assert r.status_code == 405
