from fastapi import APIRouter, Request, Response
from app.gateway.proxy import reverse_proxy

router = APIRouter(prefix="/conversations", tags=["Conversation Routing"])

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def route_conversations(request: Request, path: str) -> Response:
    """
    Proxies all requests starting with /api/v1/conversations to the Conversation Service.
    """
    return await reverse_proxy(request)
