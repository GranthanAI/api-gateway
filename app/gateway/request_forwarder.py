from fastapi import Request
from app.core.client_ip import FORWARDING_HEADERS, resolve_client
from app.core.config import settings
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
    # Identity is set only from the validated JWT below; a client-supplied
    # value (any casing) must never be forwarded.
    "x-user-id",
    # Staff role and the billing shared secret are likewise set by the gateway only.
    "x-staff-role",
    "x-gateway-secret",
]

class RequestForwarder:
    """
    Prepares headers, content, query parameters, and cookies from the incoming FastAPI request
    to be forwarded downstream, stripping connection/hop-by-hop headers and injecting context tracing.
    """
    async def prepare_request(
        self, request: Request, *, only_headers: frozenset[str] | None = None
    ) -> tuple[dict, bytes, dict, dict]:
        """
        Returns (headers, body_content, query_params, cookies) for downstream forwarding.

        only_headers: for a public machine-to-machine call (the Razorpay webhook) forward ONLY these client headers
        (lowercase names): no cookies, no Authorization (also not from the access_token cookie), no X-User-Id.
        The body is always the raw request bytes.
        """
        if only_headers is not None:
            headers = {k: v for k, v in request.headers.items() if k.lower() in only_headers}
            client_ip, forwarded_for = resolve_client(request, settings.trusted_proxy_networks)
            headers["X-Forwarded-For"] = forwarded_for
            headers["X-Real-IP"] = client_ip
            correlation_id = get_correlation_id()
            if correlation_id:
                headers["X-Correlation-ID"] = correlation_id
                headers["X-Request-ID"] = correlation_id
            return headers, await request.body(), dict(request.query_params), {}

        headers = {}
        for k, v in request.headers.items():
            if k.lower() not in HOP_BY_HOP_HEADERS and k.lower() not in FORWARDING_HEADERS:
                headers[k] = v
                
        # Real client address, derived from the TCP peer (and trusted proxies only); never copied from the client.
        client_ip, forwarded_for = resolve_client(request, settings.trusted_proxy_networks)
        headers["X-Forwarded-For"] = forwarded_for
        headers["X-Real-IP"] = client_ip

        # Inject tracing correlation context headers
        correlation_id = get_correlation_id()
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
            headers["X-Request-ID"] = correlation_id
            headers["X-Trace-ID"] = correlation_id
            
        # Propagate authenticated user ID from token claims
        if hasattr(request.state, "user_id"):
            headers["X-User-Id"] = str(request.state.user_id)
            
        # Ensure Bearer Authorization header is forwarded downstream even if it came from a cookie
        if "authorization" not in headers:
            token = request.cookies.get("access_token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
            
        body = await request.body()
        return headers, body, dict(request.query_params), dict(request.cookies)

request_forwarder = RequestForwarder()
