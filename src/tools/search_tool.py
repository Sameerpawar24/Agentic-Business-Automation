from langchain_core.tools import tool
from sqlalchemy.orm import Session
from src.database.base import SessionLocal
from src.models.invoice import Invoice
import json


def _get_db() -> Session:
    return SessionLocal()


@tool
def search_documents(query: str) -> str:
    """
    Search invoices by keyword across customer name, email, status, and notes.
    Args:
        query: Keyword or phrase to search for.
    Returns:
        JSON string with matching invoice records.
    """
    db = _get_db()
    try:
        q = f"%{query.lower()}%"
        results = (
            db.query(Invoice)
            .filter(
                Invoice.customer_name.ilike(q)
                | Invoice.customer_email.ilike(q)
                | Invoice.status.ilike(q)
                | Invoice.notes.ilike(q)
            )
            .all()
        )
        data = [
            {
                "id": inv.id,
                "customer_name": inv.customer_name,
                "customer_email": inv.customer_email,
                "amount": inv.amount,
                "status": inv.status,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
            }
            for inv in results
        ]
        if not data:
            return f"No documents found matching '{query}'."
        return json.dumps(data)
    finally:
        db.close()
