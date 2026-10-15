from fastapi import APIRouter, Request, Response
from app.gateway.proxy import reverse_proxy

router = APIRouter(prefix="/files", tags=["File Routing"])

@router.api_route("", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"], include_in_schema=False)
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"], include_in_schema=False)
async def route_files(request: Request, path: str = "") -> Response:
    """
    Proxies all requests starting with /api/v1/files to the File Service.
    The File Service's /internal/** endpoints are never routed (see gateway/router.py).
    """
    return await reverse_proxy(request)
