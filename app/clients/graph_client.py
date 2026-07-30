import httpx
from app.core.config import settings

class GraphClient:
    """
    Thin client stub wrapping downstream HTTP calls to the Graph Service.
    """
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client
        self.base_url = settings.GRAPH_SERVICE_URL
