import httpx
from app.core.config import settings

class ConversationClient:
    """
    Thin client stub wrapping downstream HTTP calls to the Conversation Service.
    """
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client
        self.base_url = settings.CONVERSATION_SERVICE_URL
