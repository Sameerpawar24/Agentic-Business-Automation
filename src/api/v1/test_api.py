from fastapi import APIRouter
from src.services.chat import ChatService
from src.core.config import settings


app = APIRouter(tags=["Test"], prefix="/test")


@app.get("/test")
async def test():
    return {"message": "This is a test endpoint"}   


# @app.post("/chat")
# async def chat(message: str):
#     chat_service = ChatService(api_key=settings.GROQ_API_KEY)
#     response = chat_service.send_message(message)
#     return {"response": response}