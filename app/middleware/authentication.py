import jwt
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.jwt_service import jwt_service
from app.core.logging import logger
from app.gateway.paths import is_public_path

class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow CORS preflight OPTIONS requests without validation
        if request.method == "OPTIONS":
            return await call_next(request)

        # Bypass auth for public paths
        path = request.url.path
        if is_public_path(path, request.method):
            return await call_next(request)

        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            token = request.cookies.get("access_token")

        # SSE clients (EventSource) cannot set custom headers, so the stream
        # route accepts a ?token= query parameter as a fallback, matching
        # Conversation Service's own get_current_user dependency.
        if not token and path.startswith("/api/v1/stream/"):
            token = request.query_params.get("token")

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
            # Staff roles (auth-service issues them from P4); a missing or malformed claim means no roles.
            roles = payload.get("roles")
            request.state.roles = [r for r in roles if isinstance(r, str)] if isinstance(roles, list) else []
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

