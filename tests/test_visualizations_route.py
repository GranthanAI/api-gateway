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
    ("/api/v1/visualizations/manim/jobs", "/api/v1/visualizations/manim/jobs"),
    ("/api/v1/visualizations/manim/jobs/mj_abc/media", "/api/v1/visualizations/manim/jobs/mj_abc/media"),
])
def test_routes_to_llm_service(path, target):
    assert gateway_router.route_request(path) == ("llm", target)


@pytest.mark.parametrize("path", [
    "/api/v1/visualizations", "/api/v1/visualizations/internal/repair", "/api/internal/visualizations/repair",
    "/api/v1/visualizations/../internal/x", "/api/v1/visualizationsx/config",
])
def test_internal_and_lookalike_paths_not_routed(path):
    assert gateway_router.route_request(path) is None


def _token():
    return jwt.encode({"sub": USER, "iss": settings.JWT_ISSUER, "exp": int(time.time()) + 600}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _client(handler):
    app.state.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TestClient(app)


def test_requires_auth_and_overrides_client_user_id_and_passes_video_bytes():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["user"] = request.headers.get("x-user-id")
        return httpx.Response(200, content=b"\x00\x00\x00\x18ftypmp42" + bytes(range(256)), headers={"content-type": "video/mp4"})

    c = _client(handler)
    assert c.get("/api/v1/visualizations/manim/jobs/mj_x/media").status_code == 401
    r = c.get("/api/v1/visualizations/manim/jobs/mj_x/media", headers={"Authorization": f"Bearer {_token()}", "X-User-Id": "attacker"})
    assert r.status_code == 200 and r.content[4:8] == b"ftyp" and r.headers["content-type"] == "video/mp4"
    assert seen["user"] == USER
