import httpx
from fastapi import Response

HOP_BY_HOP_HEADERS = [
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "content-length",
]

class ResponseHandler:
    """
    Sanitizes response headers returned from backend services, removes connection
    specific descriptors, and encapsulates payload back into FastAPI responses.
    """
    def format_response(self, response: httpx.Response) -> Response:
        headers = {}
        for k, v in response.headers.items():
            if k.lower() not in HOP_BY_HOP_HEADERS:
                headers[k] = v
                
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=headers,
            media_type=response.headers.get("content-type"),
        )

response_handler = ResponseHandler()
