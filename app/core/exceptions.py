class GatewayException(Exception):
    """Base exception class for all Gateway domain exceptions."""
    pass

class ServiceUnavailableException(GatewayException):
    """Exception raised when a downstream microservice is unreachable."""
    pass
