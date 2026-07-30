import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")
CORRELATION_ID_HEADER = "X-Correlation-ID"

def get_correlation_id() -> str:
    """Returns the current request's correlation ID or an empty string."""
    return _correlation_id_ctx.get("")

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        token = _correlation_id_ctx.set(correlation_id)

        try:
            response: Response = await call_next(request)
        finally:
            _correlation_id_ctx.reset(token)

        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
