from fastapi import FastAPI
from app.middleware.correlation import CorrelationIDMiddleware
from app.middleware.authentication import AuthenticationMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.exception_handler import ExceptionHandlerMiddleware
from app.middleware.cors import setup_cors

def register_middleware(app: FastAPI) -> None:
    """
    Registers all gateway middlewares in the correct order of precedence.
    """
    # Exception handler must be outermost to catch all inner errors
    app.add_middleware(ExceptionHandlerMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIDMiddleware)
    app.add_middleware(AuthenticationMiddleware)
    setup_cors(app)
