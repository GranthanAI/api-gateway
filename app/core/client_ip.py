"""Resolve the real client address and build the forwarding headers sent downstream.

Client-supplied forwarding headers are only honoured when the direct TCP peer is a configured trusted proxy
(TRUSTED_PROXIES); otherwise the peer address *is* the client and any incoming X-Forwarded-For / X-Real-IP /
CF-Connecting-IP value is discarded.
"""
import ipaddress
from typing import Iterable

from starlette.requests import Request

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
Network = ipaddress.IPv4Network | ipaddress.IPv6Network

# Client-controllable headers that must never be copied downstream as-is.
FORWARDING_HEADERS = frozenset({
    "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-forwarded-port",
    "x-real-ip", "forwarded", "cf-connecting-ip", "true-client-ip",
})


def parse_trusted_proxies(raw: str) -> list[Network]:
    """Parse a comma-separated list of IPs/CIDRs. Raises ValueError on a malformed entry."""
    networks: list[Network] = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            networks.append(ipaddress.ip_network(part, strict=False))
    return networks


def _parse_ip(value: str | None) -> IPAddress | None:
    if not value:
        return None
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def _is_trusted(ip: IPAddress, trusted: Iterable[Network]) -> bool:
    return any(ip in net for net in trusted)


def resolve_client(request: Request, trusted: list[Network]) -> tuple[str, str]:
    """Return (client_ip, x_forwarded_for_value) for a request."""
    peer_raw = request.client.host if request.client else ""
    peer = _parse_ip(peer_raw)
    if peer is None:
        # No usable peer (e.g. unix socket / test transport): nothing trustworthy to forward.
        return peer_raw or "unknown", peer_raw or "unknown"
    if not _is_trusted(peer, trusted):
        return str(peer), str(peer)

    chain = [ip for ip in (_parse_ip(p) for p in request.headers.get("x-forwarded-for", "").split(",")) if ip]
    chain.append(peer)

    cf_ip = _parse_ip(request.headers.get("cf-connecting-ip"))
    if cf_ip is not None:
        client = cf_ip
        if cf_ip not in chain:
            chain.insert(0, cf_ip)
    else:
        # Walk from the nearest hop outwards; the first address that is not a trusted proxy is the client.
        client = chain[0]
        for ip in reversed(chain):
            if not _is_trusted(ip, trusted):
                client = ip
                break
    return str(client), ", ".join(str(ip) for ip in chain)
