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
    "content-length",
]

def clean_hop_by_hop_headers(headers: dict) -> dict:
    """
    Strips transport-level / connection-level headers to prevent conflicts
    during reverse proxying.
    """
    cleaned = {}
    for k, v in headers.items():
        if k.lower() not in HOP_BY_HOP_HEADERS:
            cleaned[k] = v
    return cleaned
