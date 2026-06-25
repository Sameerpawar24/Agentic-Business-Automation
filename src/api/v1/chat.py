from uuid import UUID

from fastapi import APIRouter, HTTPException

from src.services.chat import ChatService
from src.services.session_service import SessionService

app = APIRouter(tags=["Chat"], prefix="/chat")


@app.post("/chat")
async def chat(message: str):
    chat_service = ChatService()
    session_service = SessionService()
    chat_session = session_service.create_chat_session(
        user_id=1, title="chat", session_type="chat"
    )
    result = chat_service.run_chat(message=message, session_id=chat_session.id)
    return {"response": result["response"], "session_id": chat_session.id}


@app.post("/chat/{session_id}")
async def chat_with_session(session_id: UUID, message: str, user_id: int = 1):
    session_id_str = str(session_id)
    chat_service = ChatService()
    session_service = SessionService()
    chat_session = session_service.get_chat_session(session_id_str)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if chat_session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Session does not belong to this user")
    result = chat_service.run_chat(message=message, session_id=session_id_str)
    return {"response": result["response"], "session_id": session_id_str}


@app.get("/get_session_id")
async def get_session_id():
    session_service = SessionService()
    sessions = session_service.get_all_session()
    return [
        {
            "id": s.id,
            "user_id": s.user_id,
            "title": s.title,
            "session_type": s.session_type,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sessions
    ]
