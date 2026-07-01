import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.database.base import SessionLocal
from src.models.workflow_run import WorkflowRun
from src.models.tool_call_log import ToolCallLog
from src.agents.orchestrator import AgentOrchestrator, AgentResult
from src.agents.planner import Planner
from src.services.log_service import LogService

logger = logging.getLogger("agentic.agent_service")

_orchestrator: Optional[AgentOrchestrator] = None
_planner: Optional[Planner] = None


def _get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


def _get_planner() -> Planner:
    global _planner
    if _planner is None:
        _planner = Planner()
    return _planner


class AgentService:
    """
    Business-layer service for agent planning, human approval, and execution.
    """

    def __init__(self):
        self.log_service = LogService()

    def create_plan(self, task: str, session_id: str) -> dict:
        """Generate a plan and persist it awaiting human approval."""
        db: Session = SessionLocal()
        try:
            plan = _get_planner().plan(task)
            run_record = WorkflowRun(
                session_id=session_id,
                workflow_type="agent_task",
                input_payload=task,
                status="awaiting_approval",
                plan=plan,
                started_at=datetime.utcnow(),
            )
            db.add(run_record)
            db.commit()
            db.refresh(run_record)
            return {
                "run_id": run_record.id,
                "session_id": session_id,
                "task": task,
                "plan": plan,
                "status": run_record.status,
            }
        finally:
            db.close()

    def approve_and_run(self, run_id: int, approved: bool = True) -> dict:
        """Approve or reject a pending plan; execute only when approved."""
        db: Session = SessionLocal()
        try:
            run_record = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
            if not run_record:
                raise ValueError(f"Workflow run {run_id} not found.")
            if run_record.status != "awaiting_approval":
                raise ValueError(
                    f"Run {run_id} is not awaiting approval (status={run_record.status})."
                )

            if not approved:
                run_record.status = "rejected"
                run_record.finished_at = datetime.utcnow()
                db.commit()
                return {
                    "run_id": run_id,
                    "session_id": run_record.session_id,
                    "task": run_record.input_payload,
                    "plan": run_record.plan or [],
                    "status": "rejected",
                    "message": "Plan rejected by user. No actions were executed.",
                }

            return self._execute_run(db, run_record)
        finally:
            db.close()

    def run(self, task: str, session_id: str) -> dict:
        """Direct execution without approval (dev / quick-run)."""
        db: Session = SessionLocal()
        try:
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
            return self._execute_run(db, run_record)
        finally:
            db.close()

    def _execute_run(self, db: Session, run_record: WorkflowRun) -> dict:
        run_id = run_record.id
        task = run_record.input_payload
        session_id = run_record.session_id
        plan = run_record.plan

        run_record.status = "running"
        db.commit()

        try:
            orchestrator = _get_orchestrator()
            result: AgentResult = orchestrator.run(
                task=task, session_id=session_id, plan=plan
            )

            if not run_record.plan:
                run_record.plan = result.plan

            run_record.status = "completed" if result.success else "failed"
            run_record.result = result.final_answer
            run_record.steps_log = result.steps
            run_record.error = result.error
            run_record.total_tokens = result.total_tokens
            run_record.duration_ms = result.duration_ms
            run_record.finished_at = datetime.utcnow()
            db.commit()

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

            for step in result.steps:
                if step.get("type") == "tool_call":
                    output = next(
                        (
                            s.get("output", "")
                            for s in result.steps
                            if s.get("type") == "tool_result"
                            and s.get("tool") == step.get("tool")
                        ),
                        "",
                    )
                    db.add(
                        ToolCallLog(
                            run_id=run_id,
                            tool_name=step.get("tool", "unknown"),
                            input=step.get("input", ""),
                            output=output,
                            latency_ms=None,
                            success=result.success,
                        )
                    )
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
                "status": run_record.status,
            }

        except Exception as exc:
            run_record.status = "failed"
            run_record.error = str(exc)
            run_record.finished_at = datetime.utcnow()
            db.commit()
            logger.error("AgentService execution failed for run_id=%d: %s", run_id, exc, exc_info=True)
            raise
