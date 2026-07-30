import httpx
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from app.gateway.router import gateway_router
from app.gateway.service_registry import service_registry
from app.gateway.request_forwarder import request_forwarder
from app.gateway.response_handler import response_handler
from app.core.logging import logger

async def reverse_proxy(request: Request) -> Response:
    """
    Coordinates routing resolution, request preparation, execution, and
    response normalization for the API Gateway proxy pathing.
    """
    route_match = gateway_router.route_request(request.url.path)
    if not route_match:
        logger.warning("Unmapped route requested", path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Gateway route not found for path: {request.url.path}"}
        )
        
    service_name, target_path = route_match
    base_url = service_registry.get_service_url(service_name)
    
    if not base_url:
        logger.error("Service base URL missing in registry", service=service_name)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Downstream service configuration missing for: {service_name}"}
        )
        
    target_url = f"{base_url.rstrip('/')}{target_path}"
    
    # 1. Prepare Request Parameters
    headers, body, params, cookies = await request_forwarder.prepare_request(request)
    
    # Get the shared AsyncClient from app state
    client: httpx.AsyncClient = request.app.state.client
    
    logger.info(
        "Routing proxy request to downstream service",
        method=request.method,
        service=service_name,
        target_url=target_url
    )
    
    try:
        # 2. Forward request downstream
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=params,
            content=body,
            cookies=cookies,
        )
    except httpx.RequestError as e:
        logger.error("Failed to connect to downstream service", service=service_name, url=target_url, error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": f"Bad gateway: service '{service_name}' is unreachable."}
        )
        
    # 3. Handle response formatting
    return response_handler.format_response(response)
