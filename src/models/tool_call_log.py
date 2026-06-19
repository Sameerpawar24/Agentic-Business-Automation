from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float
from datetime import datetime
from src.database.base import Base


class ToolCallLog(Base):
    __tablename__ = "tool_call_logs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, nullable=True, index=True)   # FK to workflow_runs.id (soft ref)
    tool_name = Column(String, nullable=False)
    input = Column(Text, nullable=True)
    output = Column(Text, nullable=True)
    latency_ms = Column(Float, nullable=True)
    success = Column(Boolean, default=True)
    error_msg = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
