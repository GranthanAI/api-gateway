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
AID = str(uuid.uuid4())


@pytest.mark.parametrize("path,target", [
    ("/api/v1/artifacts", "/v1/artifacts"),
    (f"/api/v1/artifacts/{AID}", f"/v1/artifacts/{AID}"),
    (f"/api/v1/artifacts/{AID}/media", f"/v1/artifacts/{AID}/media"),
    (f"/api/v1/artifacts/{AID}/retry", f"/v1/artifacts/{AID}/retry"),
    ("/api/v1/exports", "/v1/exports"),
    (f"/api/v1/exports/{AID}", f"/v1/exports/{AID}"),
    (f"/api/v1/exports/{AID}/download", f"/v1/exports/{AID}/download"),
])
def test_routes_to_conversation_service(path, target):
    assert gateway_router.route_request(path) == ("conversation", target)


@pytest.mark.parametrize("path", ["/api/v1/artifactsx", "/api/v1/exportsx/1", "/api/v1/artifacts/../internal/x",
                                  "/api/v1/exports/internal/x"])
def test_lookalikes_and_internal_paths_are_not_routed(path):
    assert gateway_router.route_request(path) is None


def _token():
    return jwt.encode({"sub": USER, "iss": settings.JWT_ISSUER, "exp": int(time.time()) + 600},
                      settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _client(handler):
    app.state.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TestClient(app)


@pytest.mark.parametrize("method,path", [("get", f"/api/v1/artifacts/{AID}"), ("post", "/api/v1/artifacts"),
                                         ("get", f"/api/v1/artifacts/{AID}/media"), ("post", "/api/v1/exports"),
                                         ("get", f"/api/v1/exports/{AID}/download")])
def test_all_endpoints_require_authentication(method, path):
    c = _client(lambda r: httpx.Response(200, json={}))
    assert getattr(c, method)(path).status_code == 401


def test_owner_header_is_taken_from_the_token_and_downloads_stream_through():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["user"], seen["path"] = request.headers.get("x-user-id"), request.url.path
        return httpx.Response(200, content=b"PK\x03\x04" + bytes(range(200)), headers={
            "content-type": "application/zip", "content-disposition": 'attachment; filename="x.zip"'})

    c = _client(handler)
    r = c.get(f"/api/v1/exports/{AID}/download", headers={"Authorization": f"Bearer {_token()}", "X-User-Id": "attacker"})
    assert r.status_code == 200 and r.content[:2] == b"PK" and r.headers["content-type"] == "application/zip"
    assert seen["user"] == USER and seen["path"] == f"/v1/exports/{AID}/download"
    assert "attachment" in r.headers["content-disposition"]


def test_exports_do_not_accept_mutating_verbs_other_than_post_create():
    c = _client(lambda r: httpx.Response(200, json={}))
    h = {"Authorization": f"Bearer {_token()}"}
    assert c.delete(f"/api/v1/exports/{AID}", headers=h).status_code == 405
    assert c.put("/api/v1/exports", headers=h).status_code == 405
