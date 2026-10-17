from fastapi import APIRouter, Request, Response
from app.gateway.proxy import reverse_proxy

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.get("")
async def list_tools(request: Request) -> Response:
    """
    Lists the tools that are registered AND enabled in the LLM Service right now (read-only).
    Requires a valid access token (enforced by the authentication middleware); the response holds
    tool ids, names, descriptions and parameter info only.
    """
    return await reverse_proxy(request)
