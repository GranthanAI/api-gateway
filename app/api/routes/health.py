from fastapi import APIRouter, status, Request
from app.gateway.proxy import reverse_proxy

router = APIRouter(tags=["Gateway Health"])

@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness():
    """Liveness health check for the API Gateway."""
    return {"status": "UP", "message": "Gateway process is alive."}

@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness(request: Request):
    """Readiness check verifying downstream client connection capability."""
    client_ok = hasattr(request.app.state, "client") and request.app.state.client is not None
    return {
        "status": "UP" if client_ok else "DOWN",
        "details": {"client_pool": "UP" if client_ok else "DOWN"}
    }
