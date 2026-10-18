from fastapi import APIRouter, Request, Response
from app.gateway.proxy import reverse_proxy

router = APIRouter(prefix="/memory", tags=["Memory Routing"])

# Only the user-facing memory controls are proxied. /api/v1/memory/health is answered by
# the gateway (api/routes/health.py) and memory-service's /internal/** is never routed.
@router.api_route("/settings", methods=["GET", "PUT", "OPTIONS"], include_in_schema=False)
@router.api_route("/facts", methods=["GET", "DELETE", "OPTIONS"], include_in_schema=False)
@router.api_route("/facts/{path:path}", methods=["PATCH", "DELETE", "OPTIONS"], include_in_schema=False)
async def route_memory(request: Request, path: str = "") -> Response:
    """Proxies the user's saved-memory controls to the Memory Service (JWT verified there too)."""
    return await reverse_proxy(request)
