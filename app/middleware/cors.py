from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from app.core.config import settings

def setup_cors(app: FastAPI) -> None:
    """
    Applies standard CORS policy origins, headers, and credentials permissions.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Idempotency-Key", "X-Correlation-ID", "X-Request-ID"],
    )
