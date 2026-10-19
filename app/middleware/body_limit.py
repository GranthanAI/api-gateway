"""Request body size limit (pure ASGI, so it also counts streamed/chunked bodies without buffering them).

Every API body the gateway proxies is small JSON (file bytes go straight to object storage through presigned URLs), so
an oversized body is rejected with 413 before it reaches a downstream service. The limit is configurable
(MAX_REQUEST_BODY_BYTES)."""

import json

from app.core.config import settings


class BodySizeLimitMiddleware:
    def __init__(self, app, max_bytes: int | None = None):
        self.app = app
        self._max = max_bytes

    @property
    def max_bytes(self) -> int:
        return self._max if self._max is not None else settings.MAX_REQUEST_BODY_BYTES

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        limit = self.max_bytes
        declared = next((v for k, v in scope.get("headers", []) if k == b"content-length"), None)
        if declared is not None:
            try:
                if int(declared) > limit:
                    return await self._reject(send, limit)
            except ValueError:
                return await self._reject(send, limit, status=400)

        received = 0
        started = False
        exceeded = False

        async def limited_receive():
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    exceeded = True
                    # stop feeding the application; the response below tells the client why
                    return {"type": "http.request", "body": b"", "more_body": False}
            return message

        async def guarded_send(message):
            nonlocal started
            if exceeded and not started:
                started = True
                return await self._reject(send, limit)
            if exceeded and started:
                return
            if message["type"] == "http.response.start":
                started = True
            return await send(message)

        await self.app(scope, limited_receive, guarded_send)

    @staticmethod
    async def _reject(send, limit: int, status: int = 413):
        body = json.dumps({"detail": {"code": "request_too_large" if status == 413 else "bad_request",
                                      "message": f"Request body is too large (limit {limit} bytes)." if status == 413
                                      else "Invalid Content-Length header."}}).encode()
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})
