from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import status
from fastapi.responses import JSONResponse
from app.core.logging import logger

class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """
    Catches unhandled errors globally, preventing server crash disclosures
    and ensuring responses strictly follow standard JSON error formats.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            logger.exception(
                "Unhandled gateway exception in pipeline",
                path=request.url.path,
                error=str(e)
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error: an unexpected error occurred on the gateway."}
            )
