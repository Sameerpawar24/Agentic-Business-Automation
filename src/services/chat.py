from langchain_groq import ChatGroq
from src.core.config import settings


class ChatService:
    """
    Thin wrapper around ChatGroq for simple conversational messages.
    Uses the model configured in settings (defaults to llama3-70b-8192).
    """

    def __init__(self, api_key: str):
        self.chatgroq = ChatGroq(api_key=api_key, model=settings.CHAT_MODEL)

    def send_message(self, message: str) -> str:
        """Send a plain message and return the text response."""
        response = self.chatgroq.invoke(message)
        return response.content

    # Alias so both chat.py (which calls .invoke) and new code works
    def invoke(self, message: str) -> str:
        return self.send_message(message)
