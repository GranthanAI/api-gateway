from fastapi import APIRouter, Request, Response
from app.gateway.proxy import reverse_proxy

router = APIRouter(prefix="/exports", tags=["Exports"])


@router.api_route("", methods=["POST", "OPTIONS"], include_in_schema=False)
@router.api_route("/{path:path}", methods=["GET", "OPTIONS"], include_in_schema=False)
async def route_exports(request: Request, path: str = "") -> Response:
    """
    Proxies /api/v1/exports (conversation / hierarchy export jobs and their authenticated downloads) to the
    Conversation Service. Requires a valid access token; the owner is taken from that token downstream.
    """
    return await reverse_proxy(request)
