from src.database.base import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy import Enum

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)

    session_id = Column(
        String(36),
        ForeignKey("chat_sessions.id"),
        nullable=False,
    )

    role = Column(String, nullable=False)
    # user, assistant, system, tool

    content = Column(Text, nullable=False)

    tokens = Column(Integer, default=0)

    meta = Column("metadata", JSON)  # renamed: 'metadata' is reserved by SQLAlchemy Declarative

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    session = relationship(
        "ChatSession",
        back_populates="messages"
    )