from fastapi import Request
import httpx

def get_http_client(request: Request) -> httpx.AsyncClient:
    """Returns the shared AsyncClient from request state."""
    return request.app.state.client
