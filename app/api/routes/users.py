from fastapi import APIRouter, Request, Response
from app.gateway.proxy import reverse_proxy

router = APIRouter(prefix="/users", tags=["Users Routing"])

@router.api_route("", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"], include_in_schema=False)
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"], include_in_schema=False)
async def route_users(request: Request, path: str = "") -> Response:
    """
    Proxies all requests starting with /api/v1/users to the Auth Service.
    """
    return await reverse_proxy(request)
