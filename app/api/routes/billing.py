from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.gateway.paths import is_billing_public, normalize_path
from app.gateway.proxy import reverse_proxy

router = APIRouter(prefix="/billing", tags=["Billing"])

STAFF_ROLES = ("billing_admin", "support")  # highest first
# The only client headers the Razorpay webhook forwards; nothing else (no cookies, no Authorization).
WEBHOOK_HEADERS = frozenset({"content-type", "x-razorpay-signature", "x-razorpay-event-id"})


def _forbidden() -> Response:
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Insufficient permissions."})


@router.api_route("", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"], include_in_schema=False)
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"], include_in_schema=False)
async def route_billing(request: Request, path: str = "") -> Response:
    """
    Proxies /api/v1/billing/* to billing-service (mapping in gateway/router.py). Adds X-Gateway-Secret (billing only),
    and X-Staff-Role on staff / simulator-control routes after the role check. billing-service's /internal/** is never
    routed. Public paths are decided by the authentication middleware (gateway/paths.py).
    """
    norm = normalize_path(request.url.path)
    parts = (norm or "").split("/")  # ["", "billing", <head>, ...]
    head = parts[2] if len(parts) > 2 else ""
    roles = getattr(request.state, "roles", [])
    extra = {"X-Gateway-Secret": settings.BILLING_GATEWAY_SECRET}

    if norm is not None and norm == "/billing/webhooks/razorpay" and request.method == "POST":
        # The money path: raw bytes and the signature headers only (no cookies, no Authorization, no identity).
        return await reverse_proxy(request, extra_headers=extra, only_headers=WEBHOOK_HEADERS)

    if head == "sim" and not settings.BILLING_SIM_ROUTES:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Not found."})

    if head == "admin":
        staff = next((r for r in STAFF_ROLES if r in roles), None)
        if staff is None:
            return _forbidden()
        extra["X-Staff-Role"] = staff
    elif head == "sim" and not is_billing_public(norm or "", request.method):
        # Simulator control API: billing_admin, or a user listed in DEV_MODE_USERS (outside production).
        user = str(getattr(request.state, "user_id", "")).lower()
        if "billing_admin" not in roles and user not in settings.dev_mode_users:
            return _forbidden()
        extra["X-Staff-Role"] = "billing_admin"

    return await reverse_proxy(request, extra_headers=extra)
