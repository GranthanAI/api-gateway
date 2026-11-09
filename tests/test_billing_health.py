"""P3x: billing in the gateway's downstream health and readiness checks, and the public /billing/health probe."""

import httpx

from tests.conftest import bearer


def test_billing_health_probe_needs_no_jwt_and_proxies_readyz(gateway):
    gateway.respond = lambda req: httpx.Response(200, json={"status": "ready"})
    r = gateway.client.get("/api/v1/billing/health")
    assert r.status_code == 200 and r.json() == {"status": "ready"}
    (up,) = gateway.calls
    assert up.url.path == "/readyz" and "x-gateway-secret" not in up.headers


def test_billing_health_reports_unhealthy_when_billing_is_down(gateway):
    def boom(req):
        raise httpx.ConnectError("down")
    gateway.respond = boom
    r = gateway.client.get("/api/v1/billing/health")
    assert r.status_code == 200 and r.json()["status"] == "unhealthy"


def test_info_lists_billing(gateway):
    gateway.respond = lambda req: httpx.Response(200, json={})
    r = gateway.client.get("/api/v1/info")
    assert r.json()["services"]["billing"] == "UP"
    assert any(c.url.path == "/healthz" for c in gateway.calls)


def test_ready_reports_billing_without_depending_on_it(gateway):
    gateway.respond = lambda req: httpx.Response(503, json={"status": "not_ready"})
    r = gateway.client.get("/api/v1/ready").json()
    assert r["status"] == "UP" and r["details"]["billing"] == "NOT_READY"

    def boom(req):
        raise httpx.ConnectError("down")
    gateway.respond = boom
    r = gateway.client.get("/api/v1/ready").json()
    assert r["status"] == "UP" and r["details"]["billing"] == "DOWN"
    gateway.respond = lambda req: httpx.Response(200, json={"status": "ready"})
    assert gateway.client.get("/api/v1/ready").json()["details"]["billing"] == "UP"


def test_a_non_probe_billing_path_still_needs_a_jwt(gateway):
    assert gateway.client.get("/api/v1/billing/me").status_code == 401
    assert gateway.client.get("/api/v1/billing/me", headers=bearer()).status_code == 200
