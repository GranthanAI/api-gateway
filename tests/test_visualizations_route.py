import time
import uuid

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.gateway.router import gateway_router
from app.main import app

USER = str(uuid.uuid4())


@pytest.mark.parametrize("path,target", [
    ("/api/v1/visualizations/config", "/api/v1/visualizations/config"),
    ("/api/v1/visualizations/repair", "/api/v1/visualizations/repair"),
])
def test_routes_to_llm_service(path, target):
    assert gateway_router.route_request(path) == ("llm", target)


@pytest.mark.parametrize("path", [
    "/api/v1/visualizations", "/api/v1/visualizations/internal/repair", "/api/internal/visualizations/repair",
    "/api/v1/visualizations/../internal/x", "/api/v1/visualizationsx/config",
    # the raw Manim job API is internal now: renders go through the artifact registry only
    "/api/v1/visualizations/manim/jobs", "/api/v1/visualizations/manim/jobs/mj_abc", "/api/v1/visualizations/manim/jobs/mj_abc/media",
])
def test_internal_and_lookalike_paths_not_routed(path):
    assert gateway_router.route_request(path) is None


def _token():
    return jwt.encode({"sub": USER, "iss": settings.JWT_ISSUER, "exp": int(time.time()) + 600}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _client(handler):
    app.state.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TestClient(app)


def test_repair_requires_auth_and_overrides_client_user_id():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["user"] = request.headers.get("x-user-id")
        return httpx.Response(200, json={"ok": False})

    c = _client(handler)
    assert c.post("/api/v1/visualizations/repair", json={}).status_code == 401
    r = c.post("/api/v1/visualizations/repair", json={"kind": "mermaid", "content": "x", "attempt": 2},
               headers={"Authorization": f"Bearer {_token()}", "X-User-Id": "attacker"})
    assert r.status_code == 200 and seen["user"] == USER


def test_the_raw_manim_job_api_is_not_reachable_through_the_gateway():
    c = _client(lambda r: httpx.Response(200, json={}))
    h = {"Authorization": f"Bearer {_token()}"}
    assert c.post("/api/v1/visualizations/manim/jobs", json={"spec": {}}, headers=h).status_code in (404, 405)
    assert c.get("/api/v1/visualizations/manim/jobs/mj_x/media", headers=h).status_code in (404, 405)
