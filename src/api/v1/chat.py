from fastapi import APIRouter
from src.services.chat import ChatService
from src.core.config import settings


app = APIRouter(tags=["Chat"], prefix="/chat")
 


@app.post("/chat")
async def chat(message: str):
    chat_service = ChatService(api_key=settings.GROQ_API_KEY)
    response = chat_service.invoke(message)
    return {"response": response}