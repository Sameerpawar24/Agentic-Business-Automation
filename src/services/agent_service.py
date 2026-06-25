import logging
import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from src.database.base import SessionLocal
from src.models.workflow_run import WorkflowRun
from src.models.tool_call_log import ToolCallLog
from src.agents.orchestrator import AgentOrchestrator, AgentResult
from src.services.log_service import LogService

logger = logging.getLogger("agentic.agent_service")

# Singleton orchestrator — instantiated once, reused across requests
_orchestrator: Optional[AgentOrchestrator] = None


def _get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


class AgentService:
    """
    Business-layer service that:
    1. Delegates task execution to AgentOrchestrator
    2. Persists WorkflowRun record in the DB
    3. Persists ToolCallLog records for every tool call made
    4. Writes unified ActivityLog entries
    """

    def __init__(self):
        self.log_service = LogService()

    def run(self, task: str, session_id: str) -> dict:
        """
        Run a task through the agent and return a serializable result dict.
        Also writes audit records to the database.
        """
        db: Session = SessionLocal()
        run_record = WorkflowRun(
            session_id=session_id,
            workflow_type="agent_task",
            input_payload=task,
            status="running",
            started_at=datetime.utcnow(),
        )
        db.add(run_record)
        db.commit()
        db.refresh(run_record)
        run_id = run_record.id

        try:
            orchestrator = _get_orchestrator()
            result: AgentResult = orchestrator.run(task=task, session_id=session_id)

            # Update WorkflowRun
            run_record.status = "completed" if result.success else "failed"
            run_record.result = result.final_answer
            run_record.steps_log = result.steps
            run_record.error = result.error
            run_record.total_tokens = result.total_tokens
            run_record.duration_ms = result.duration_ms
            run_record.finished_at = datetime.utcnow()
            db.commit()

            # Unified activity log
            try:
                self.log_service.create(
                    log_type="agent",
                    session_id=session_id,
                    run_id=run_id,
                    task=task,
                    message=task,
                    response=result.final_answer,
                    model_name=result.model_name,
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    total_tokens=result.total_tokens,
                    latency_ms=round(result.duration_ms, 2),
                    success=result.success,
                    error=result.error,
                    meta={
                        "plan": result.plan,
                        "tool_calls_made": result.tool_calls_made,
                        "steps": result.steps,
                    },
                    db=db,
                )
            except Exception as log_exc:
                logger.warning("Could not persist agent activity log: %s", log_exc)

            # Log each tool call
            for step in result.steps:
                if step.get("type") == "tool_call":
                    # Find matching tool_result
                    output = next(
                        (
                            s.get("output", "")
                            for s in result.steps
                            if s.get("type") == "tool_result"
                            and s.get("tool") == step.get("tool")
                        ),
                        "",
                    )
                    log = ToolCallLog(
                        run_id=run_id,
                        tool_name=step.get("tool", "unknown"),
                        input=step.get("input", ""),
                        output=output,
                        latency_ms=None,
                        success=result.success,
                    )
                    db.add(log)
            db.commit()

            return {
                "run_id": run_id,
                "session_id": session_id,
                "task": task,
                "plan": result.plan,
                "steps": result.steps,
                "tool_calls_made": result.tool_calls_made,
                "final_answer": result.final_answer,
                "duration_ms": round(result.duration_ms, 2),
                "success": result.success,
                "error": result.error,
            }

        except Exception as exc:
            run_record.status = "failed"
            run_record.error = str(exc)
            run_record.finished_at = datetime.utcnow()
            db.commit()
            logger.error("AgentService.run failed for run_id=%d: %s", run_id, exc, exc_info=True)
            raise
        finally:
            db.close()
