import json
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
CID = str(uuid.uuid4())
NOTES = f"/api/v1/conversations/{CID}/notes"


def test_notes_route_to_the_conversation_service():
    assert gateway_router.route_request(NOTES) == ("conversation", f"/v1/conversations/{CID}/notes")


def _token():
    return jwt.encode({"sub": USER, "iss": settings.JWT_ISSUER, "exp": int(time.time()) + 600},
                      settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _client(handler):
    app.state.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TestClient(app)


def test_get_and_put_require_authentication():
    c = _client(lambda r: httpx.Response(200, json={}))
    assert c.get(NOTES).status_code == 401
    assert c.put(NOTES, json={"content": "x", "version": 0}).status_code == 401


def test_put_forwards_method_body_and_the_owner_from_the_token_not_the_client():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(method=request.method, path=request.url.path, user=request.headers.get("x-user-id"),
                    body=json.loads(request.content or b"{}"))
        return httpx.Response(200, json={"content": "x", "version": 1})

    c = _client(handler)
    r = c.put(NOTES, json={"content": "# hi", "version": 0},
              headers={"Authorization": f"Bearer {_token()}", "X-User-Id": "attacker"})
    assert r.status_code == 200
    assert seen["method"] == "PUT" and seen["path"] == f"/v1/conversations/{CID}/notes"
    assert seen["user"] == USER and seen["body"] == {"content": "# hi", "version": 0}


def test_a_version_conflict_and_its_current_document_pass_through_unchanged():
    detail = {"code": "version_conflict", "message": "Your notes were changed elsewhere.",
              "current": {"content": "theirs", "version": 3}}
    c = _client(lambda r: httpx.Response(409, json={"detail": detail}))
    r = c.put(NOTES, json={"content": "mine", "version": 2}, headers={"Authorization": f"Bearer {_token()}"})
    assert r.status_code == 409 and r.json()["detail"] == detail


def test_notes_bodies_over_the_gateway_limit_are_refused_before_reaching_the_service():
    called = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        called["n"] += 1
        return httpx.Response(200, json={})

    c = _client(handler)
    big = "a" * (settings.MAX_REQUEST_BODY_BYTES + 10)
    r = c.put(NOTES, content=json.dumps({"content": big, "version": 0}),
              headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"})
    assert r.status_code == 413 and called["n"] == 0
