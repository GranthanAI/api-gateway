import httpx
from app.core.config import settings

class AuthClient:
    """
    Thin client stub wrapping downstream HTTP calls to the Auth Service.
    """
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client
        self.base_url = settings.AUTH_SERVICE_URL
