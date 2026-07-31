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
    def format_response(self, response: httpx.Response, request_path: str = "") -> Response:
        headers = {}
        for k, v in response.headers.items():
            if k.lower() not in HOP_BY_HOP_HEADERS:
                headers[k] = v
                
        fastapi_response = Response(
            content=response.content,
            status_code=response.status_code,
            headers=headers,
            media_type=response.headers.get("content-type"),
        )

        # Handle HttpOnly access_token cookie persistence for production session management
        if response.status_code == 200:
            if request_path.endswith("/auth/login") or request_path.endswith("/auth/refresh"):
                try:
                    data = response.json()
                    access_token = data.get("access_token")
                    expires_in = data.get("expires_in", 900)
                    if access_token:
                        fastapi_response.set_cookie(
                            key="access_token",
                            value=access_token,
                            httponly=True,
                            secure=True,
                            samesite="strict",
                            path="/",
                            max_age=expires_in
                        )
                except Exception:
                    pass
            elif request_path.endswith("/auth/logout"):
                fastapi_response.delete_cookie(key="access_token", path="/")

        return fastapi_response

response_handler = ResponseHandler()
