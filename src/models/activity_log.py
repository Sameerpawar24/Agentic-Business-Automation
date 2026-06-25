from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, JSON

from src.database.base import Base


class ActivityLog(Base):
    """
    Unified audit log for chat and agent interactions.
    Captures model, tokens, messages, latency, and task details in one place.
    """

    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    log_type = Column(String, nullable=False, index=True)  # chat | agent
    session_id = Column(String(36), nullable=True, index=True)
    run_id = Column(Integer, nullable=True, index=True)    # workflow_runs.id for agent runs

    task = Column(Text, nullable=True)           # agent task (null for chat)
    message = Column(Text, nullable=True)        # user input
    response = Column(Text, nullable=True)       # assistant / final output

    model_name = Column(String, nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    latency_ms = Column(Float, nullable=True)
    success = Column(Boolean, default=True)
    error = Column(Text, nullable=True)
    meta = Column("metadata", JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
