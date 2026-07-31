import httpx
from fastapi import APIRouter, status, Request
from app.core.config import settings
from app.core.logging import logger

router = APIRouter(tags=["Gateway Health & Information"])

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

@router.get("/info", status_code=status.HTTP_200_OK)
async def gateway_info(request: Request):
    """
    Exposes gateway version and the connectivity health status of all registered
    downstream microservices (Auth, Conversation, Graph).
    """
    client: httpx.AsyncClient = request.app.state.client
    services = {}
    
    # Define check targets
    checks = [
        ("auth", settings.AUTH_SERVICE_URL, "/health"),
        ("conversation", settings.CONVERSATION_SERVICE_URL, "/v1/health/live"),
        ("graph", settings.GRAPH_SERVICE_URL, "/graph/health")
    ]
    
    for name, base_url, path in checks:
        target_url = f"{base_url.rstrip('/')}{path}"
        try:
            # Quick ping to confirm downstream process connectivity
            resp = await client.get(target_url, timeout=2.0)
            # Both 200 OK and 503 Service Unavailable (degraded dependencies) mean process is UP
            if resp.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]:
                services[name] = "UP"
            else:
                services[name] = "DEGRADED"
        except Exception as e:
            logger.debug(f"Health ping failed for service {name}", error=str(e))
            services[name] = "DOWN"
            
    return {
        "gateway_version": "1.0.0",
        "services": services
    }

# --- Proxied Microservice Health Checks for consistency ---

@router.get("/auth/health", status_code=status.HTTP_200_OK, tags=["Gateway Health & Information"])
async def auth_health(request: Request):
    """Proxies request to Auth Service health check endpoint."""
    client: httpx.AsyncClient = request.app.state.client
    target_url = f"{settings.AUTH_SERVICE_URL.rstrip('/')}/health"
    try:
        resp = await client.get(target_url, timeout=5.0)
        return resp.json()
    except Exception as e:
        logger.error("Auth health check proxy failed", error=str(e))
        return {"status": "unhealthy", "detail": "Auth microservice is offline or timed out."}

@router.get("/conversations/health", status_code=status.HTTP_200_OK, tags=["Gateway Health & Information"])
async def conversation_health(request: Request):
    """Proxies request to Conversation Service health check endpoint."""
    client: httpx.AsyncClient = request.app.state.client
    target_url = f"{settings.CONVERSATION_SERVICE_URL.rstrip('/')}/v1/health/ready"
    try:
        resp = await client.get(target_url, timeout=5.0)
        return resp.json()
    except Exception as e:
        logger.error("Conversation health check proxy failed", error=str(e))
        return {"status": "unhealthy", "detail": "Conversation microservice is offline or timed out."}

@router.get("/graph/health", status_code=status.HTTP_200_OK, tags=["Graph"])
async def graph_health(request: Request):
    """Proxies request to Graph Service health check endpoint."""
    client: httpx.AsyncClient = request.app.state.client
    target_url = f"{settings.GRAPH_SERVICE_URL.rstrip('/')}/graph/health"
    try:
        resp = await client.get(target_url, timeout=5.0)
        return resp.json()
    except Exception as e:
        logger.error("Graph health check proxy failed", error=str(e))
        return {"status": "unhealthy", "detail": "Graph microservice is offline or timed out."}
