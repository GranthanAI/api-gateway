"""P3: billing routes through the gateway, against a stub upstream."""

import gzip
import hashlib

import httpx
import pytest

from app.core.config import Settings, settings
from app.gateway.router import gateway_router
from tests.conftest import bearer

SECRET = settings.BILLING_GATEWAY_SECRET
USER = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def sim(monkeypatch):
    monkeypatch.setattr(settings, "BILLING_SIM_ROUTES", True)


@pytest.mark.parametrize("path,target", [
    ("/api/v1/billing/plans", "/billing/v1/plans"),
    ("/api/v1/billing/me/models", "/billing/v1/me/models"),
    ("/api/v1/billing/invoices/abc/pdf", "/billing/v1/invoices/abc/pdf"),
    ("/api/v1/billing/wallet/topups", "/billing/v1/wallet/topups"),
    ("/api/v1/billing/admin/accounts/1", "/admin/billing/v1/accounts/1"),
    ("/api/v1/billing/webhooks/razorpay", "/billing/v1/webhooks/razorpay"),
])
def test_routes_map_to_the_right_upstream_path(path, target):
    assert gateway_router.route_request(path) == ("billing", target)


def test_sim_routes_map_only_when_enabled(sim):
    assert gateway_router.route_request("/api/v1/billing/sim/checkout/x") == ("billing", "/billing/v1/sim/checkout/x")
    assert gateway_router.route_request("/api/v1/billing/sim/clock/advance") == ("billing", "/billing/v1/sim/clock/advance")


def test_sim_routes_are_not_routed_when_disabled():
    assert gateway_router.route_request("/api/v1/billing/sim/checkout/x") is None


@pytest.mark.parametrize("path", [
    "/api/v1/billing/internal/x", "/api/v1/billing/v1/internal/x", "/api/v1/billing/Internal", "/api/v1/billing/admin",
    "/api/v1/billing", "/api/v1/billing/", "/api/v1/billing/plans/../admin/x", "/api/v1/billing/%2e%2e/x",
])
def test_internal_traversal_and_bare_prefixes_are_not_routed(path, sim):
    assert gateway_router.route_request(path) is None


@pytest.mark.parametrize("path", ["/api/v1/billing/internal/x", "/api/v1/billing/v1/internal/x"])
def test_internal_is_404_end_to_end(gateway, path):
    assert gateway.client.get(path, headers=bearer()).status_code == 404 and gateway.calls == []


def test_gateway_secret_only_on_billing_calls(gateway):
    gateway.client.get("/api/v1/billing/me", headers=bearer())
    gateway.client.get("/api/v1/files", headers=bearer())
    gateway.client.get("/api/v1/conversations", headers=bearer())
    billing, *others = gateway.calls
    assert billing.headers["x-gateway-secret"] == SECRET and billing.headers["x-user-id"] == USER
    assert all("x-gateway-secret" not in o.headers for o in others)


def test_client_sent_secret_never_passed_on(gateway):
    gateway.client.get("/api/v1/billing/me", headers={**bearer(), "X-Gateway-Secret": "attacker"})
    gateway.client.get("/api/v1/files", headers={**bearer(), "X-Gateway-Secret": "attacker"})
    assert gateway.calls[0].headers.get_list("x-gateway-secret") == [SECRET]
    assert "x-gateway-secret" not in gateway.calls[1].headers


def test_billing_requires_a_jwt_except_public_paths(gateway):
    assert gateway.client.get("/api/v1/billing/me").status_code == 401
    assert gateway.client.get("/api/v1/billing/plans").status_code == 200
    assert gateway.client.get("/api/v1/billing/models").status_code == 200
    assert gateway.client.post("/api/v1/billing/checkout", json={}).status_code == 401
    assert gateway.client.get("/api/v1/billing/webhooks/razorpay").status_code == 401  # only POST is public
    assert gateway.client.get("/api/v1/billing/plans/x").status_code == 401
    assert gateway.client.get("/api/v1/billing/plans/../me").status_code == 401


def test_spoofed_staff_role_and_user_id_on_user_routes_are_dropped(gateway):
    gateway.client.get("/api/v1/billing/me", headers={**bearer(), "X-Staff-Role": "billing_admin", "x-user-id": "evil"})
    (up,) = gateway.calls
    assert "x-staff-role" not in up.headers and up.headers["x-user-id"] == USER


def test_admin_without_role_is_403_and_never_proxied(gateway):
    assert gateway.client.get("/api/v1/billing/admin/accounts", headers=bearer()).status_code == 403
    r = gateway.client.get("/api/v1/billing/admin/accounts",
                           headers={**bearer(roles=["user"]), "X-Staff-Role": "billing_admin"})
    assert r.status_code == 403 and gateway.calls == []
    assert gateway.client.get("/api/v1/billing/admin/accounts").status_code == 401


@pytest.mark.parametrize("roles,expected", [
    (["support"], "support"), (["billing_admin"], "billing_admin"), (["support", "billing_admin"], "billing_admin"),
    (["x", "support"], "support"),
])
def test_admin_staff_role_header(gateway, roles, expected):
    r = gateway.client.get("/api/v1/billing/admin/accounts/7", headers={**bearer(roles=roles), "X-Staff-Role": "evil"})
    (up,) = gateway.calls
    assert r.status_code == 200 and up.url.path == "/admin/billing/v1/accounts/7"
    assert up.headers.get_list("x-staff-role") == [expected] and up.headers["x-gateway-secret"] == SECRET


def test_malformed_roles_claim_means_no_roles(gateway):
    assert gateway.client.get("/api/v1/billing/admin/a", headers=bearer(roles="billing_admin")).status_code == 403
    assert gateway.client.get("/api/v1/billing/admin/a", headers=bearer(roles=[1, None])).status_code == 403


def test_sim_routes_404_when_flag_off(gateway):
    assert gateway.client.get("/api/v1/billing/sim/checkout/abc", headers=bearer()).status_code == 404
    assert gateway.client.get("/api/v1/billing/sim/clock", headers=bearer(roles=["billing_admin"])).status_code == 404
    assert gateway.client.get("/api/v1/billing/sim/checkout/abc").status_code == 401  # auth first; never proxied
    assert gateway.calls == []


def test_public_sim_checkout_without_jwt_when_enabled(gateway, sim):
    assert gateway.client.get("/api/v1/billing/sim/checkout/abc?t=tok").status_code == 200
    assert gateway.client.post("/api/v1/billing/sim/checkout/abc/pay", json={}).status_code == 200
    g, p = gateway.calls
    assert g.url.path == "/billing/v1/sim/checkout/abc" and g.url.params["t"] == "tok"
    assert p.url.path == "/billing/v1/sim/checkout/abc/pay"
    assert g.headers["x-gateway-secret"] == SECRET and "x-staff-role" not in g.headers
    assert gateway.client.get("/api/v1/billing/sim/checkout/abc/pay").status_code == 401  # wrong method
    assert gateway.client.get("/api/v1/billing/sim/checkout/abc/extra/x").status_code == 401


def test_sim_control_needs_billing_admin_or_dev_mode_user(gateway, sim, monkeypatch):
    url = "/api/v1/billing/sim/clock/advance"
    assert gateway.client.post(url).status_code == 401
    assert gateway.client.post(url, headers=bearer()).status_code == 403
    assert gateway.client.post(url, headers=bearer(roles=["support"])).status_code == 403
    assert gateway.calls == []
    r = gateway.client.post(url, headers={**bearer(roles=["billing_admin"]), "X-Staff-Role": "support"})
    assert r.status_code == 200
    monkeypatch.setattr(settings, "DEV_MODE_USERS", f"someone, {USER.upper()}")
    assert gateway.client.post(url, headers=bearer()).status_code == 200
    assert len(gateway.calls) == 2
    for up in gateway.calls:
        assert up.headers.get_list("x-staff-role") == ["billing_admin"]
        assert up.url.path == "/billing/v1/sim/clock/advance"


def test_idempotency_key_is_forwarded_unchanged(gateway):
    gateway.client.post("/api/v1/billing/checkout", json={"plan": "pro"},
                        headers={**bearer(), "Idempotency-Key": "k-123"})
    assert gateway.calls[0].headers["idempotency-key"] == "k-123"


# --- webhook: raw bytes -------------------------------------------------------------------

WEBHOOK_BODIES = [
    '{"event":"payment.captured","note":"₹499 — café ✓","n":1}\n'.encode(),
    b'{"a":1,\r\n "b":"x"}\r\n',
    b'{"event":"x"}\n\n',
    b'{ "k" : "v" }  ',
    '{"raw":"₹"}'.encode("utf-16"),  # not even UTF-8
    bytes(range(256)),
]


@pytest.mark.parametrize("body", WEBHOOK_BODIES)
def test_webhook_body_is_identical_upstream(gateway, body):
    r = gateway.client.post(
        "/api/v1/billing/webhooks/razorpay", content=body,
        headers={"Content-Type": "application/json; charset=utf-8", "X-Razorpay-Signature": "sig123",
                 "x-razorpay-event-id": "evt_1", "Cookie": "access_token=abc", "Authorization": "Bearer attacker",
                 "X-User-Id": "evil", "X-Staff-Role": "billing_admin"},
    )
    assert r.status_code == 200
    (up,) = gateway.calls
    assert hashlib.sha256(up.content).hexdigest() == hashlib.sha256(body).hexdigest()
    assert up.url.path == "/billing/v1/webhooks/razorpay"
    assert up.headers["x-razorpay-signature"] == "sig123" and up.headers["x-razorpay-event-id"] == "evt_1"
    assert up.headers["content-type"] == "application/json; charset=utf-8"
    assert up.headers["x-gateway-secret"] == SECRET
    for h in ("cookie", "authorization", "x-user-id", "x-staff-role"):
        assert h not in up.headers


def test_webhook_ignores_cookies_and_the_cookie_to_bearer_fallback(gateway):
    gateway.client.cookies.set("access_token", "cookie-token")
    try:
        gateway.client.post("/api/v1/billing/webhooks/razorpay", content=b"{}",
                            headers={"Content-Type": "application/json"})
    finally:
        gateway.client.cookies.clear()
    (up,) = gateway.calls
    assert "authorization" not in up.headers and "cookie" not in up.headers


def test_webhook_limit_is_at_least_one_mb(gateway):
    assert Settings(_env_file=None).MAX_REQUEST_BODY_BYTES >= 1_048_576
    body = b"x" * 1_048_576
    assert gateway.client.post("/api/v1/billing/webhooks/razorpay", content=body).status_code == 200
    assert len(gateway.calls[0].content) == len(body)
    assert gateway.client.post("/api/v1/billing/webhooks/razorpay", content=body + b"x").status_code == 413


# --- PDF ----------------------------------------------------------------------------------

def test_pdf_bytes_and_headers_are_preserved(gateway):
    pdf = b"%PDF-1.7\n" + bytes(range(256)) * 40 + b"\r\n%%EOF\n"
    gateway.respond = lambda req: httpx.Response(
        200, content=pdf, headers={"Content-Type": "application/pdf",
                                   "Content-Disposition": 'attachment; filename="GA-2627-000001.pdf"'})
    r = gateway.client.get("/api/v1/billing/invoices/abc/pdf", headers=bearer())
    assert r.content == pdf and r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == 'attachment; filename="GA-2627-000001.pdf"'


def test_gzipped_upstream_body_is_not_double_encoded(gateway):
    pdf = b"%PDF-1.7 " + bytes(range(256)) * 10
    gateway.respond = lambda req: httpx.Response(
        200, content=gzip.compress(pdf), headers={"Content-Type": "application/pdf", "Content-Encoding": "gzip"})
    r = gateway.client.get("/api/v1/billing/invoices/abc/pdf", headers=bearer())
    assert r.content == pdf and "content-encoding" not in r.headers


# --- production guard ---------------------------------------------------------------------

STRONG = "k9Qx2mV7pLr4Zt8WyB3nHd6Fs1JcUe5A"
PROD = dict(ENVIRONMENT="production", JWT_SECRET_KEY=STRONG,
            BILLING_GATEWAY_SECRET="Bq7Lm3Xv9Tn2Zc6Rw4Hy8Kd1Pf5Ja0Ue")


def test_production_starts_with_strong_billing_config():
    Settings(_env_file=None, **PROD)
    Settings(_env_file=None, BILLING_SIM_ROUTES=True)  # development may enable the simulator


@pytest.mark.parametrize("secret", ["", "dev-gateway-secret", "short"])
def test_production_refuses_empty_default_or_weak_billing_secret(secret):
    with pytest.raises(ValueError) as exc:
        Settings(_env_file=None, **{**PROD, "BILLING_GATEWAY_SECRET": secret})
    assert "BILLING_GATEWAY_SECRET" in str(exc.value)


def test_production_refuses_the_default_secret_when_unset():
    with pytest.raises(ValueError, match="BILLING_GATEWAY_SECRET"):
        Settings(_env_file=None, ENVIRONMENT="production", JWT_SECRET_KEY=STRONG)


@pytest.mark.parametrize("env", ["production", " Prod "])
def test_production_refuses_sim_routes(env):
    with pytest.raises(ValueError, match="BILLING_SIM_ROUTES"):
        Settings(_env_file=None, **{**PROD, "ENVIRONMENT": env, "BILLING_SIM_ROUTES": True})


# --- canonical upstream path (P3x) ---------------------------------------------------------

@pytest.mark.parametrize("path", [
    "/api/v1/billing/webhooks/razorpay/", "/api/v1/billing//webhooks/razorpay",
    "/api/v1/billing//webhooks//razorpay//", "/api/v1/billing/webhooks/razorpay",
])
def test_webhook_noncanonical_paths_reach_the_exact_upstream_path_with_identical_bytes(gateway, path):
    body = '{"event":"payment.captured","note":"₹499 — café"}\r\n'.encode()
    r = gateway.client.post(path, content=body, headers={"Content-Type": "application/json",
                                                         "X-Razorpay-Signature": "sig", "x-razorpay-event-id": "e1"})
    assert r.status_code == 200
    (up,) = gateway.calls
    assert up.url.path == "/billing/v1/webhooks/razorpay"
    assert hashlib.sha256(up.content).hexdigest() == hashlib.sha256(body).hexdigest()
    assert up.headers["x-razorpay-signature"] == "sig" and "authorization" not in up.headers


@pytest.mark.parametrize("path,target", [
    ("/api/v1/billing/plans/", "/billing/v1/plans"),
    ("/api/v1/billing//me//models", "/billing/v1/me/models"),
    ("/api/v1/billing/Invoices/AbC/pdf/", "/billing/v1/Invoices/AbC/pdf"),   # case is kept
    ("/api/v1/billing//admin//accounts/", "/admin/billing/v1/accounts"),
])
def test_billing_forwards_the_normalised_path_without_lowercasing(path, target):
    assert gateway_router.route_request(path) == ("billing", target)


def test_noncanonical_admin_path_is_still_gated(gateway):
    assert gateway.client.get("/api/v1/billing//admin//x/", headers=bearer()).status_code == 403
    assert gateway.calls == []


def test_production_refuses_dev_mode_users():
    with pytest.raises(ValueError, match="DEV_MODE_USERS"):
        Settings(_env_file=None, **{**PROD, "DEV_MODE_USERS": USER})
    Settings(_env_file=None, DEV_MODE_USERS=USER)       # development may use it
    Settings(_env_file=None, **{**PROD, "DEV_MODE_USERS": " , "})  # blank entries do not count
