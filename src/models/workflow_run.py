from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float
from datetime import datetime
from src.database.base import Base


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=True, index=True)
    workflow_type = Column(String, nullable=False, default="agent_task")
    input_payload = Column(Text, nullable=False)        # raw task text
    status = Column(String, default="pending")          # awaiting_approval | rejected | running | completed | failed
    plan = Column(JSON, nullable=True)                  # planner steps awaiting approval
    steps_log = Column(JSON, nullable=True)             # execution step dicts
    result = Column(Text, nullable=True)                # final agent answer
    error = Column(Text, nullable=True)
    total_tokens = Column(Integer, default=0)
    duration_ms = Column(Float, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
