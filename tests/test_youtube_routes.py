import json
import time
import uuid

import httpx
import jwt
from fastapi.testclient import TestClient

from app.core.config import settings
from app.gateway.router import gateway_router
from app.main import app

USER = str(uuid.uuid4())
DOC = str(uuid.uuid4())


def _token():
    return jwt.encode({"sub": USER, "iss": settings.JWT_ISSUER, "exp": int(time.time()) + 600},
                      settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _client(handler):
    app.state.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TestClient(app)


def test_youtube_routes_go_to_the_file_service_unchanged():
    assert gateway_router.route_request("/files/youtube") == ("file", "/files/youtube")
    assert gateway_router.route_request(f"/files/youtube/{DOC}") == ("file", f"/files/youtube/{DOC}")
    assert gateway_router.route_request(f"/files/youtube/{DOC}/retry") == ("file", f"/files/youtube/{DOC}/retry")


def test_internal_routes_remain_unreachable_through_the_youtube_prefix():
    assert gateway_router.route_request("/files/youtube/../internal/files/permissions/check") is None


def test_every_method_requires_authentication():
    c = _client(lambda r: httpx.Response(200, json={}))
    assert c.post("/api/v1/files/youtube", json={"url": "https://youtu.be/dQw4w9WgXcQ"}).status_code == 401
    assert c.get(f"/api/v1/files/youtube/{DOC}").status_code == 401
    assert c.post(f"/api/v1/files/youtube/{DOC}/retry").status_code == 401
    assert c.delete(f"/api/v1/files/youtube/{DOC}").status_code == 401


def test_requests_are_forwarded_with_the_caller_taken_from_the_token_not_the_client():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, request.headers.get("x-user-id"), json.loads(request.content or b"{}")))
        return httpx.Response(202 if request.method == "POST" else 200, json={"document_id": DOC})

    c = _client(handler)
    h = {"Authorization": f"Bearer {_token()}", "X-User-Id": "attacker"}
    assert c.post("/api/v1/files/youtube", json={"url": "https://youtu.be/dQw4w9WgXcQ", "conversation_id": DOC}, headers=h).status_code == 202
    assert c.get(f"/api/v1/files/youtube/{DOC}", headers=h).status_code == 200
    assert seen[0][:3] == ("POST", "/files/youtube", USER)
    assert seen[0][3] == {"url": "https://youtu.be/dQw4w9WgXcQ", "conversation_id": DOC}
    assert seen[1][:3] == ("GET", f"/files/youtube/{DOC}", USER)


def test_validation_errors_and_quota_pass_through_with_their_status():
    c = _client(lambda r: httpx.Response(422, json={"error_code": "InvalidYouTubeUrl", "message": "x", "reason": "unsupported_host"}))
    r = c.post("/api/v1/files/youtube", json={"url": "https://evil.com/x"}, headers={"Authorization": f"Bearer {_token()}"})
    assert r.status_code == 422 and r.json()["reason"] == "unsupported_host"
    c = _client(lambda r: httpx.Response(429, json={"error_code": "YoutubeQuotaExceeded"}, headers={"Retry-After": "3600"}))
    r = c.post("/api/v1/files/youtube", json={"url": "https://youtu.be/dQw4w9WgXcQ"}, headers={"Authorization": f"Bearer {_token()}"})
    assert r.status_code == 429
