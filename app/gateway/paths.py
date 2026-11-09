"""Path normalisation and the public-path decision, shared by the authentication middleware and the OpenAPI aggregator.

Matching is EXACT on a normalised path (never "contains"): a path that merely mentions /health or /info must still
authenticate. Anything odd (dot segments, encoded dots/slashes, backslashes) is never public.
"""

import re

from app.core.config import settings

API_PREFIX = "/api/v1"

PUBLIC_EXACT = frozenset({
    "/openapi.json",
    "/auth/login", "/auth/register", "/auth/refresh", "/auth/verify-email", "/auth/resend-verification",
    "/auth/forgot-password", "/auth/reset-password",
    "/health", "/ready", "/live", "/info",
    # health probes the gateway answers itself (api/routes/health.py)
    "/auth/health", "/conversations/health", "/graph/health", "/llm/health", "/memory/health",
})
# Docs assets only; matched on a segment boundary ("/docs" or "/docs/...").
PUBLIC_PREFIXES = ("/docs", "/redoc")

_SLASHES = re.compile(r"/{2,}")
_ENCODED_TRICKS = re.compile(r"%(2e|2f|5c)", re.IGNORECASE)


def normalize_path(path: str) -> str | None:
    """Strip a leading /api/v1, collapse duplicate slashes, strip one trailing slash, lowercase.
    Returns None for a path with "." / ".." segments, encoded dots/slashes or backslashes."""
    if "\\" in path or _ENCODED_TRICKS.search(path):
        return None
    if any(seg in (".", "..") for seg in path.split("/")):
        return None
    if path == API_PREFIX or path.startswith(API_PREFIX + "/"):
        path = path[len(API_PREFIX):]
    path = _SLASHES.sub("/", path)
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return (path or "/").lower()


def is_billing_public(norm: str, method: str) -> bool:
    """Billing paths that need no JWT (norm is already normalised)."""
    method = method.upper()
    if method == "GET" and norm in ("/billing/plans", "/billing/models"):
        return True
    if method == "POST" and norm == "/billing/webhooks/razorpay":
        return True
    if getattr(settings, "BILLING_SIM_ROUTES", False):
        parts = norm.split("/")  # ["", "billing", "sim", "checkout", "<id>", ("pay")]
        if parts[:4] == ["", "billing", "sim", "checkout"] and len(parts) >= 5 and parts[4]:
            if method == "GET" and len(parts) == 5:
                return True
            if method == "POST" and len(parts) == 6 and parts[5] == "pay":
                return True
    return False


def is_public_path(path: str, method: str = "GET") -> bool:
    norm = normalize_path(path)
    if norm is None:
        return False
    if norm in PUBLIC_EXACT:
        return True
    if any(norm == p or norm.startswith(p + "/") for p in PUBLIC_PREFIXES):
        return True
    return is_billing_public(norm, method)
