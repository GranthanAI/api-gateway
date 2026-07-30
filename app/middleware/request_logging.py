import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.logging import logger

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all processed HTTP requests with status code, response time, and path context.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        response: Response = await call_next(request)
        
        duration = time.time() - start_time
        logger.info(
            "Processed HTTP request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=int(duration * 1000)
        )
        return response
