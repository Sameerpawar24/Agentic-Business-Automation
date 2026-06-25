from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database.base import get_db
from src.services.log_service import LogService, activity_log_to_dict

app = APIRouter(prefix="/logs", tags=["Logs"])

log_service = LogService()


@app.get("/", summary="List activity logs")
async def list_logs(
    log_type: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Return unified activity logs (chat + agent).

    Filter by `log_type` (`chat` or `agent`) or `session_id`.
    Each record includes model name, tokens, message, latency, and task.
    """
    logs = log_service.list_logs(
        db,
        log_type=log_type,
        session_id=session_id,
        limit=limit,
        offset=offset,
    )
    return [activity_log_to_dict(log) for log in logs]


@app.get("/{log_id}", summary="Get a single activity log")
async def get_log(log_id: int, db: Session = Depends(get_db)):
    log = log_service.get_by_id(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail=f"Log {log_id} not found.")
    return activity_log_to_dict(log)
