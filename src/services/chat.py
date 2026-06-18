from langchain_groq import ChatGroq
from src.core.config import settings
      
class ChatService:
    def __init__(self, api_key: str):
        self.chatgroq = ChatGroq(api_key=api_key, model='openai/gpt-oss-120b')

    def send_message(self, message: str) -> str:
        response = self.chatgroq.invoke(message)
        return response.content
    
