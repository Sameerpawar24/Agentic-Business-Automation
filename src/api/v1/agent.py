import uuid

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from src.database.base import get_db
from src.models.workflow_run import WorkflowRun
from src.services.agent_service import AgentService
import logging

logger = logging.getLogger("agentic.api.agent")

app = APIRouter(prefix="/agent", tags=["Agent"])

agent_service = AgentService()


# ── Request / Response Schemas ─────────────────────────────────────────────────

class AgentRunRequest(BaseModel):
    task: str
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class AgentApproveRequest(BaseModel):
    run_id: int
    approved: bool = True


class AgentRunResponse(BaseModel):
    run_id: int
    session_id: str
    task: str
    plan: list
    steps: list = []
    tool_calls_made: list = []
    final_answer: str = ""
    duration_ms: float = 0.0
    success: bool = True
    error: str | None = None
    status: str | None = None


class AgentPlanResponse(BaseModel):
    run_id: int
    session_id: str
    task: str
    plan: list
    status: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.post("/plan", response_model=AgentPlanResponse, summary="Generate plan for human approval")
async def plan_agent(request: AgentRunRequest):
    """
    Step 1: Generate a plan from the task and wait for human approval.
    No tools are executed until `/agent/approve` is called with `approved: true`.
    """
    try:
        return agent_service.create_plan(task=request.task, session_id=request.session_id)
    except Exception as exc:
        logger.error("Agent plan failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/approve", summary="Approve or reject a pending plan")
async def approve_agent(request: AgentApproveRequest):
    """
    Step 2: Approve to execute the plan, or reject to cancel without running tools.
    """
    try:
        return agent_service.approve_and_run(run_id=request.run_id, approved=request.approved)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Agent approve failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/run", response_model=AgentRunResponse, summary="Run an agentic task (skip approval)")
async def run_agent(request: AgentRunRequest):
    """
    Execute immediately without human approval (quick-run / dev mode).
    """
    try:
        result = agent_service.run(task=request.task, session_id=request.session_id)
        return result
    except Exception as exc:
        logger.error("Agent run failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/history", summary="List all past workflow runs")
async def get_history(limit: int = 20, db: Session = Depends(get_db)):
    """Return the most recent workflow runs ordered by start time."""
    runs = (
        db.query(WorkflowRun)
        .order_by(WorkflowRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "run_id": r.id,
            "session_id": r.session_id,
            "status": r.status,
            "workflow_type": r.workflow_type,
            "input_payload": r.input_payload,
            "plan": r.plan or [],
            "result": r.result,
            "duration_ms": r.duration_ms,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        }
        for r in runs
    ]


@app.get("/run/{run_id}", summary="Get details for a specific workflow run")
async def get_run(run_id: int, db: Session = Depends(get_db)):
    """Return full detail of a workflow run including step-by-step log."""
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Workflow run {run_id} not found.")
    return {
        "run_id": run.id,
        "session_id": run.session_id,
        "status": run.status,
        "workflow_type": run.workflow_type,
        "input_payload": run.input_payload,
        "plan": run.plan or [],
        "steps_log": run.steps_log or [],
        "result": run.result,
        "error": run.error,
        "duration_ms": run.duration_ms,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }
