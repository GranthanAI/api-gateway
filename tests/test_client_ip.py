"""Client IP resolution and X-Forwarded-For / X-Real-IP propagation."""

import pytest
from starlette.requests import Request

from app.core.client_ip import parse_trusted_proxies, resolve_client
from app.gateway.request_forwarder import request_forwarder


def make_request(peer: str | None, headers: dict[str, str] | None = None) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http", "method": "GET", "path": "/", "query_string": b"", "headers": raw,
        "client": (peer, 5000) if peer else None,
    }
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


LB = parse_trusted_proxies("10.0.0.0/8")


def test_untrusted_peer_ignores_client_supplied_headers():
    req = make_request("203.0.113.9", {"X-Forwarded-For": "1.2.3.4", "CF-Connecting-IP": "5.6.7.8"})
    assert resolve_client(req, LB) == ("203.0.113.9", "203.0.113.9")


def test_empty_trusted_list_trusts_nobody():
    req = make_request("10.1.1.1", {"X-Forwarded-For": "1.2.3.4"})
    assert resolve_client(req, []) == ("10.1.1.1", "10.1.1.1")


def test_trusted_peer_appends_to_chain_and_picks_first_untrusted_from_right():
    req = make_request("10.0.0.5", {"X-Forwarded-For": "6.6.6.6, 198.51.100.7, 10.0.0.9"})
    client, chain = resolve_client(req, LB)
    assert client == "198.51.100.7"  # 6.6.6.6 is a spoofed prefix, not the nearest untrusted hop
    assert chain == "6.6.6.6, 198.51.100.7, 10.0.0.9, 10.0.0.5"


def test_trusted_peer_without_xff_uses_peer():
    assert resolve_client(make_request("10.0.0.5"), LB) == ("10.0.0.5", "10.0.0.5")


def test_cf_connecting_ip_preferred_from_trusted_peer():
    req = make_request("10.0.0.5", {"CF-Connecting-IP": "198.51.100.7", "X-Forwarded-For": "9.9.9.9"})
    client, chain = resolve_client(req, LB)
    assert client == "198.51.100.7"
    assert chain.startswith("198.51.100.7") and chain.endswith("10.0.0.5")


def test_garbage_values_are_dropped():
    req = make_request("10.0.0.5", {"X-Forwarded-For": "not-an-ip, 198.51.100.7", "CF-Connecting-IP": "zzz"})
    assert resolve_client(req, LB) == ("198.51.100.7", "198.51.100.7, 10.0.0.5")


def test_malformed_trusted_proxies_rejected():
    with pytest.raises(ValueError):
        parse_trusted_proxies("10.0.0.0/8, nope")


@pytest.mark.asyncio
async def test_forwarded_request_never_carries_client_supplied_forwarding_headers():
    req = make_request("203.0.113.9", {
        "X-Forwarded-For": "1.2.3.4", "X-Real-IP": "1.2.3.4", "CF-Connecting-IP": "1.2.3.4", "Forwarded": "for=1.2.3.4",
    })
    headers, *_ = await request_forwarder.prepare_request(req)
    lowered = {k.lower(): v for k, v in headers.items()}
    assert lowered["x-forwarded-for"] == "203.0.113.9"
    assert lowered["x-real-ip"] == "203.0.113.9"
    assert "cf-connecting-ip" not in lowered and "forwarded" not in lowered
    assert sum(1 for k in headers if k.lower() == "x-forwarded-for") == 1
