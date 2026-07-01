import json
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.services.chat import ChatService
from src.services.session_service import SessionService

app = APIRouter(tags=["Chat"], prefix="/chat")

_chat_service = ChatService()


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _stream_response(message: str, session_id: str):
    """SSE generator — yields token chunks then a done event."""
    try:
        for token in _chat_service.stream_chat(message=message, session_id=session_id):
            yield _sse({"token": token})
        yield _sse({"done": True, "session_id": session_id})
    except Exception as exc:
        yield _sse({"error": str(exc), "done": True, "session_id": session_id})


@app.post("/stream")
async def chat_stream(message: str):
    """Start a new chat session and stream the assistant response (SSE)."""
    session_service = SessionService()
    chat_session = session_service.create_chat_session(
        user_id=1, title="chat", session_type="chat"
    )
    return StreamingResponse(
        _stream_response(message, chat_session.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/stream/{session_id}")
async def chat_stream_session(session_id: UUID, message: str, user_id: int = 1):
    """Continue an existing session with a streamed response (SSE)."""
    session_id_str = str(session_id)
    session_service = SessionService()
    chat_session = session_service.get_chat_session(session_id_str)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if chat_session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Session does not belong to this user")

    return StreamingResponse(
        _stream_response(message, session_id_str),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/chat")
async def chat(message: str):
    session_service = SessionService()
    chat_session = session_service.create_chat_session(
        user_id=1, title="chat", session_type="chat"
    )
    result = _chat_service.run_chat(message=message, session_id=chat_session.id)
    return {"response": result["response"], "session_id": chat_session.id}


@app.post("/chat/{session_id}")
async def chat_with_session(session_id: UUID, message: str, user_id: int = 1):
    session_id_str = str(session_id)
    session_service = SessionService()
    chat_session = session_service.get_chat_session(session_id_str)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if chat_session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Session does not belong to this user")
    result = _chat_service.run_chat(message=message, session_id=session_id_str)
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
