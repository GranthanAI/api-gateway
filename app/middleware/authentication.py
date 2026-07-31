import jwt
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.jwt_service import jwt_service
from app.core.logging import logger

PUBLIC_PATHS = [
    "/openapi.json",
    "/docs",
    "/redoc",
    "/auth/login",
    "/auth/register",
    "/auth/refresh",
    "/auth/verify-email",
    "/auth/resend-verification",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/health",
    "/ready",
    "/live",
    "/info",
]

class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow CORS preflight OPTIONS requests without validation
        if request.method == "OPTIONS":
            return await call_next(request)

        # Bypass auth for public paths
        path = request.url.path
        if any(p in path for p in PUBLIC_PATHS):
            return await call_next(request)

        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            token = request.cookies.get("access_token")

        if not token:
            logger.warning("Missing or invalid authentication credentials", path=path)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication credentials were not provided or are malformed."}
            )
        try:
            payload = jwt_service.decode_token(token)
            # Store validated user identity in request state for downstream headers injection
            request.state.user_id = payload["sub"]
        except jwt.ExpiredSignatureError:
            logger.warning("Expired JWT token signature presented", path=path)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Access token has expired."}
            )
        except jwt.PyJWTError as e:
            logger.warning("Invalid JWT signature/claims", path=path, error=str(e))
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid access token."}
            )

        return await call_next(request)

