import logging
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy.orm import Session

from src.database.base import SessionLocal
from src.models.activity_log import ActivityLog

logger = logging.getLogger("agentic.log_service")


class LogService:
    """Persist and query unified activity logs."""

    def create(
        self,
        log_type: str,
        *,
        session_id: Optional[str] = None,
        run_id: Optional[int] = None,
        task: Optional[str] = None,
        message: Optional[str] = None,
        response: Optional[str] = None,
        model_name: Optional[str] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        latency_ms: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None,
        meta: Optional[dict] = None,
        db: Optional[Session] = None,
    ) -> ActivityLog:
        owns_db = db is None
        if owns_db:
            db = SessionLocal()

        try:
            record = ActivityLog(
                log_type=log_type,
                session_id=session_id,
                run_id=run_id,
                task=task,
                message=message,
                response=response,
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                success=success,
                error=error,
                meta=meta,
                created_at=datetime.utcnow(),
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            logger.info(
                "Activity log #%d | type=%s | model=%s | tokens=%d | %.1f ms",
                record.id,
                log_type,
                model_name or "unknown",
                total_tokens,
                latency_ms or 0,
            )
            return record
        except Exception as exc:
            db.rollback()
            logger.error("Failed to write activity log: %s", exc, exc_info=True)
            raise
        finally:
            if owns_db:
                db.close()

    def list_logs(
        self,
        db: Session,
        *,
        log_type: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ActivityLog]:
        query = db.query(ActivityLog).order_by(ActivityLog.created_at.desc())
        if log_type:
            query = query.filter(ActivityLog.log_type == log_type)
        if session_id:
            query = query.filter(ActivityLog.session_id == session_id)
        return query.offset(offset).limit(limit).all()

    def get_by_id(self, db: Session, log_id: int) -> Optional[ActivityLog]:
        return db.query(ActivityLog).filter(ActivityLog.id == log_id).first()


def activity_log_to_dict(log: ActivityLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "log_type": log.log_type,
        "session_id": log.session_id,
        "run_id": log.run_id,
        "task": log.task,
        "message": log.message,
        "response": log.response,
        "model_name": log.model_name,
        "prompt_tokens": log.prompt_tokens,
        "completion_tokens": log.completion_tokens,
        "total_tokens": log.total_tokens,
        "latency_ms": log.latency_ms,
        "success": log.success,
        "error": log.error,
        "metadata": log.meta,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }
