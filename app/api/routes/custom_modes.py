from fastapi import APIRouter, Request, Response
from app.gateway.proxy import reverse_proxy

router = APIRouter(prefix="/custom-modes", tags=["Custom Modes Routing"])

@router.api_route("", methods=["GET", "POST", "OPTIONS"], include_in_schema=False)
@router.api_route("/{path:path}", methods=["GET", "PATCH", "DELETE", "OPTIONS"], include_in_schema=False)
async def route_custom_modes(request: Request, path: str = "") -> Response:
    """
    Proxies /api/v1/custom-modes (a user's reusable custom modes) to the Conversation Service, which owns them.
    Requires a valid access token; the owner is taken from that token downstream (the gateway strips any
    client-supplied X-User-Id), never from the request body.
    """
    return await reverse_proxy(request)
