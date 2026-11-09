"""Shared harness: the real gateway app with a stub upstream (httpx.MockTransport) instead of real services."""

import time
from types import SimpleNamespace
from urllib.parse import unquote

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def make_token(sub: str = "11111111-1111-1111-1111-111111111111", **claims) -> str:
    payload = {"sub": sub, "iss": settings.JWT_ISSUER, "exp": int(time.time()) + 600, **claims}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def bearer(**kw) -> dict:
    return {"Authorization": f"Bearer {make_token(**kw)}"}


@pytest.fixture
def gateway():
    """.client talks to the gateway; .calls records every upstream request (httpx.Request);
    set .respond to a callable(httpx.Request) -> httpx.Response to change the stub's answer."""
    calls: list[httpx.Request] = []
    state = SimpleNamespace(calls=calls, respond=lambda req: httpx.Response(200, json={"ok": True}))

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return state.respond(request)

    previous = getattr(app.state, "client", None)
    app.state.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    state.client = TestClient(app, raise_server_exceptions=False)  # no `with`: lifespan (real client) not started
    yield state
    app.state.client = previous


async def asgi_status(path: str, method: str = "GET", query: bytes = b"") -> int:
    """Calls the whole gateway with a RAW ASGI path (no client-side dot-segment normalisation).
    `path` is what a server hands the app: already percent-decoded."""
    sent: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method,
        "scheme": "http", "path": unquote(path), "raw_path": path.encode(), "query_string": query,
        "headers": [(b"host", b"gw")], "client": ("127.0.0.1", 1), "server": ("gw", 80), "root_path": "",
    }
    await app(scope, receive, send)
    return next(m["status"] for m in sent if m["type"] == "http.response.start")
