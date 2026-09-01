from fastapi import APIRouter, Request, Response
from app.gateway.proxy import reverse_proxy_stream

router = APIRouter(prefix="/stream", tags=["SSE Stream"])

@router.api_route("/{path:path}", methods=["GET"], include_in_schema=False)
async def route_stream(request: Request, path: str = "") -> Response:
    """
    Proxies /api/v1/stream/{conversation_id} to the Conversation Service's SSE
    endpoint, streaming the response body live instead of buffering it, so
    real-time token generation reaches the client as it happens.
    """
    return await reverse_proxy_stream(request)
