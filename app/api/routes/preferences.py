from fastapi import APIRouter, Request, Response
from app.gateway.proxy import reverse_proxy

router = APIRouter(prefix="/preferences", tags=["Preferences Routing"])

@router.api_route("", methods=["GET", "PATCH", "DELETE", "OPTIONS"], include_in_schema=False)
@router.api_route("/{path:path}", methods=["GET", "PATCH", "DELETE", "OPTIONS"], include_in_schema=False)
async def route_preferences(request: Request, path: str = "") -> Response:
    """
    Proxies /api/v1/preferences (the user's AI / application preferences) to the
    Conversation Service, which owns them. Requires a valid access token.
    """
    return await reverse_proxy(request)
