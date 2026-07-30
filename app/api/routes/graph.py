from fastapi import APIRouter, Request, Response
from app.gateway.proxy import reverse_proxy

router = APIRouter(prefix="/graph", tags=["Graph Routing"])

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def route_graph(request: Request, path: str) -> Response:
    """
    Proxies all requests starting with /api/v1/graph to the Graph Service.
    """
    return await reverse_proxy(request)
