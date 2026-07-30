from fastapi import Request
from app.middleware.correlation import get_correlation_id

HOP_BY_HOP_HEADERS = [
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
]

class RequestForwarder:
    """
    Prepares headers, content, query parameters, and cookies from the incoming FastAPI request
    to be forwarded downstream, stripping connection/hop-by-hop headers and injecting context tracing.
    """
    async def prepare_request(self, request: Request) -> tuple[dict, bytes, dict, dict]:
        """
        Returns (headers, body_content, query_params, cookies) for downstream forwarding.
        """
        headers = {}
        for k, v in request.headers.items():
            if k.lower() not in HOP_BY_HOP_HEADERS:
                headers[k] = v
                
        # Inject tracing correlation context headers
        correlation_id = get_correlation_id()
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
            headers["X-Request-ID"] = correlation_id
            headers["X-Trace-ID"] = correlation_id
            
        # Propagate authenticated user ID from token claims
        if hasattr(request.state, "user_id"):
            headers["X-User-Id"] = str(request.state.user_id)
            
        body = await request.body()
        return headers, body, dict(request.query_params), dict(request.cookies)

request_forwarder = RequestForwarder()
