from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
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
    session_id: str = "default-session"


class AgentRunResponse(BaseModel):
    run_id: int
    session_id: str
    task: str
    plan: list
    steps: list
    tool_calls_made: list
    final_answer: str
    duration_ms: float
    success: bool
    error: str | None = None


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.post("/run", response_model=AgentRunResponse, summary="Run an agentic task")
async def run_agent(request: AgentRunRequest):
    """
    Execute a natural-language business task using the ReAct agent.

    **Example tasks:**
    - "Find all unpaid invoices and send reminder emails to customers"
    - "Generate a full business analytics summary report"
    - "Search for invoices related to Acme Corp"
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
        "plan": [],
        "steps_log": run.steps_log or [],
        "result": run.result,
        "error": run.error,
        "duration_ms": run.duration_ms,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }
