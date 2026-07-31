from fastapi import APIRouter, Request, Response
from app.gateway.proxy import reverse_proxy

router = APIRouter(prefix="/auth", tags=["Auth Routing"])

@router.api_route("", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"], include_in_schema=False)
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"], include_in_schema=False)
async def route_auth(request: Request, path: str = "") -> Response:
    """
    Proxies all requests starting with /api/v1/auth to the Auth Service.
    """
    return await reverse_proxy(request)
