from app.core.config import settings

class ServiceRegistry:
    """
    Registry mapping logical service names to their backend base URLs.
    """
    def __init__(self) -> None:
        self._services = {
            "auth": settings.AUTH_SERVICE_URL,
            "conversation": settings.CONVERSATION_SERVICE_URL,
            "graph": settings.GRAPH_SERVICE_URL
        }

    def get_service_url(self, service_name: str) -> str | None:
        return self._services.get(service_name.lower())

service_registry = ServiceRegistry()
