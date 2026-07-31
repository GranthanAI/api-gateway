from fastapi import APIRouter, Request, Response
from app.gateway.proxy import reverse_proxy

router = APIRouter(prefix="/sessions", tags=["Sessions Routing"])

@router.api_route("", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"], include_in_schema=False)
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"], include_in_schema=False)
async def route_sessions(request: Request, path: str = "") -> Response:
    """
    Proxies all requests starting with /api/v1/sessions to the Auth Service.
    """
    return await reverse_proxy(request)
