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
CID, MID = str(uuid.uuid4()), str(uuid.uuid4())
BASE = f"/api/v1/conversations/{CID}/source-edits"
ONE = f"{BASE}/{MID}/0-L3-abcdef12"


def _token():
    return jwt.encode({"sub": USER, "iss": settings.JWT_ISSUER, "exp": int(time.time()) + 600},
                      settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _client(handler):
    app.state.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TestClient(app)


def test_source_edit_routes_map_to_the_conversation_service():
    assert gateway_router.route_request(BASE) == ("conversation", f"/v1/conversations/{CID}/source-edits")
    assert gateway_router.route_request(ONE) == ("conversation", f"/v1/conversations/{CID}/source-edits/{MID}/0-L3-abcdef12")


def test_every_method_requires_authentication():
    c = _client(lambda r: httpx.Response(200, json={}))
    assert c.get(BASE).status_code == 401
    assert c.put(ONE, json={}).status_code == 401
    assert c.delete(ONE + "?version=1").status_code == 401


def test_put_and_delete_forward_method_query_body_and_the_owner_from_the_token():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, request.url.query.decode(), request.headers.get("x-user-id"),
                     json.loads(request.content or b"{}")))
        return httpx.Response(204 if request.method == "DELETE" else 200, json={"version": 1})

    c = _client(handler)
    h = {"Authorization": f"Bearer {_token()}", "X-User-Id": "attacker"}
    body = {"content": "x = 1\n", "version": 0, "language": "python", "source_format": "code", "original_sha256": "0" * 64}
    assert c.put(ONE, json=body, headers=h).status_code == 200
    assert c.delete(ONE + "?version=3", headers=h).status_code == 204
    assert seen[0][:4] == ("PUT", f"/v1/conversations/{CID}/source-edits/{MID}/0-L3-abcdef12", "", USER)
    assert seen[0][4] == body
    assert seen[1][:4] == ("DELETE", seen[0][1], "version=3", USER)


def test_a_version_conflict_passes_through_with_the_current_edit():
    detail = {"code": "version_conflict", "current": {"content": "theirs", "version": 3}}
    c = _client(lambda r: httpx.Response(409, json={"detail": detail}))
    r = c.put(ONE, json={"content": "mine", "version": 2}, headers={"Authorization": f"Bearer {_token()}"})
    assert r.status_code == 409 and r.json()["detail"] == detail
