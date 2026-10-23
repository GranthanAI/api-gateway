from fastapi import APIRouter, Request, Response
from app.gateway.proxy import reverse_proxy

router = APIRouter(prefix="/artifacts", tags=["Artifacts"])


@router.api_route("", methods=["GET", "POST", "OPTIONS"], include_in_schema=False)
@router.api_route("/{path:path}", methods=["GET", "POST", "OPTIONS"], include_in_schema=False)
async def route_artifacts(request: Request, path: str = "") -> Response:
    """
    Proxies /api/v1/artifacts (Mermaid / Manim artifact registry, previews, downloads, retry) to the Conversation
    Service, which owns it. Requires a valid access token; the owner is taken from that token downstream (the gateway
    strips any client-supplied X-User-Id). Media is streamed through, so a video is never reachable without
    authentication.
    """
    return await reverse_proxy(request)
