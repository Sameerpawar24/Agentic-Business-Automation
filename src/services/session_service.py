import uuid
from typing import List, Optional

from src.database.base import SessionLocal
from src.models.session import ChatSession


class SessionService:
    def get_all_session(self) -> List[ChatSession]:
        db = SessionLocal()
        try:
            return db.query(ChatSession).all()
        finally:
            db.close()

    def get_session_by_id(self, session_id: str) -> Optional[ChatSession]:
        db = SessionLocal()
        try:
            return (
                db.query(ChatSession)
                .filter(ChatSession.id == str(session_id))
                .first()
            )
        finally:
            db.close()

    def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        """Alias used by the chat API."""
        return self.get_session_by_id(session_id)

    def create_chat_session(
        self,
        user_id: int = 1,
        title: str = "chat",
        session_type: str = "chat",
    ) -> ChatSession:
        db = SessionLocal()
        try:
            chat_session = ChatSession(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=title,
                session_type=session_type,
            )
            db.add(chat_session)
            db.commit()
            db.refresh(chat_session)
            return chat_session
        finally:
            db.close()
