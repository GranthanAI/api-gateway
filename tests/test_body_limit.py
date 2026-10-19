"""Oversized request bodies are rejected before they are proxied; normal ones pass untouched."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.middleware.body_limit import BodySizeLimitMiddleware


def make_app(limit: int):
    app = FastAPI()
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=limit)
    seen = {"calls": 0}

    @app.post("/echo")
    async def echo(request: Request):
        seen["calls"] += 1
        return {"size": len(await request.body())}

    return app, seen


def test_small_bodies_pass():
    app, seen = make_app(100)
    r = TestClient(app).post("/echo", content=b"x" * 100)
    assert r.status_code == 200 and r.json() == {"size": 100} and seen["calls"] == 1


def test_a_declared_oversized_body_is_rejected_without_reaching_the_application():
    app, seen = make_app(100)
    r = TestClient(app).post("/echo", content=b"x" * 101)
    assert r.status_code == 413 and r.json()["detail"]["code"] == "request_too_large" and seen["calls"] == 0


def test_a_streamed_body_without_content_length_is_still_limited():
    app, seen = make_app(100)

    def chunks():
        for _ in range(5):
            yield b"x" * 40                              # 200 bytes in total, no Content-Length

    r = TestClient(app).post("/echo", content=chunks())
    assert r.status_code == 413


def test_an_invalid_content_length_is_a_400():
    app, _ = make_app(100)
    r = TestClient(app).post("/echo", content=b"x", headers={"content-length": "abc"})
    assert r.status_code in (400, 413)


def test_the_real_gateway_applies_the_limit(monkeypatch):
    from app.core.config import settings
    from app.main import app

    monkeypatch.setattr(settings, "MAX_REQUEST_BODY_BYTES", 50)
    r = TestClient(app).post("/api/v1/auth/login", content=b"x" * 500, headers={"content-type": "application/json"})
    assert r.status_code == 413
