from app.middleware.correlation import get_correlation_id

def get_current_correlation_id() -> str:
    """Gets the active request context's correlation tracing ID."""
    return get_correlation_id()
