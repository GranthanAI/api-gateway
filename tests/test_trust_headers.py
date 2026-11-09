"""P3a: client-sent trust headers (any casing) never reach a downstream service."""

import pytest

from app.gateway.request_forwarder import HOP_BY_HOP_HEADERS
from tests.conftest import bearer

SPOOFED = ["X-Staff-Role", "x-staff-role", "X-STAFF-ROLE", "X-Gateway-Secret", "x-gateway-secret", "X-GATEWAY-SECRET",
           "X-User-Id", "x-user-id", "X-USER-ID"]
ROUTES = ["/api/v1/files", "/api/v1/conversations", "/api/v1/preferences", "/api/v1/memory/settings",
          "/api/v1/auth/login", "/api/v1/tools"]


def test_strip_list_has_the_trust_headers():
    assert {"x-user-id", "x-staff-role", "x-gateway-secret"} <= set(HOP_BY_HOP_HEADERS)


@pytest.mark.parametrize("header", SPOOFED)
@pytest.mark.parametrize("route", ROUTES)
def test_spoofed_trust_headers_never_reach_a_service(gateway, route, header):
    gateway.client.get(route, headers={**bearer(), header: "attacker"})
    (up,) = gateway.calls
    assert up.headers.get("x-staff-role") is None
    assert up.headers.get("x-gateway-secret") is None
    assert up.headers.get("x-user-id") in (None, "11111111-1111-1111-1111-111111111111")
    assert "attacker" not in up.headers.values()
