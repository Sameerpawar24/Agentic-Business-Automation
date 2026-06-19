from langchain_core.tools import tool
from sqlalchemy.orm import Session
from src.database.base import SessionLocal
from src.models.invoice import Invoice
from datetime import datetime
from typing import Optional
import json


def _get_db() -> Session:
    return SessionLocal()


@tool
def get_invoices(status: Optional[str] = None) -> str:
    """
    Retrieve invoices from the database.
    Args:
        status: Filter by status — 'paid', 'unpaid', or 'overdue'. Leave empty for all invoices.
    Returns:
        JSON string with list of matching invoices.
    """
    db = _get_db()
    try:
        query = db.query(Invoice)
        if status:
            query = query.filter(Invoice.status == status.lower())
        invoices = query.all()
        result = [
            {
                "id": inv.id,
                "customer_name": inv.customer_name,
                "customer_email": inv.customer_email,
                "amount": inv.amount,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "status": inv.status,
                "notes": inv.notes,
            }
            for inv in invoices
        ]
        return json.dumps(result)
    finally:
        db.close()


@tool
def get_invoice_by_id(invoice_id: int) -> str:
    """
    Get a single invoice by its ID.
    Args:
        invoice_id: The integer ID of the invoice.
    Returns:
        JSON string with invoice details, or an error message if not found.
    """
    db = _get_db()
    try:
        inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not inv:
            return json.dumps({"error": f"Invoice {invoice_id} not found"})
        return json.dumps({
            "id": inv.id,
            "customer_name": inv.customer_name,
            "customer_email": inv.customer_email,
            "amount": inv.amount,
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "status": inv.status,
            "notes": inv.notes,
        })
    finally:
        db.close()


@tool
def update_invoice_status(invoice_id: int, new_status: str) -> str:
    """
    Update the status of an invoice.
    Args:
        invoice_id: The integer ID of the invoice to update.
        new_status: The new status — must be 'paid', 'unpaid', or 'overdue'.
    Returns:
        Confirmation message string.
    """
    valid_statuses = {"paid", "unpaid", "overdue"}
    if new_status.lower() not in valid_statuses:
        return f"Error: invalid status '{new_status}'. Must be one of {valid_statuses}."
    db = _get_db()
    try:
        inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not inv:
            return f"Error: Invoice {invoice_id} not found."
        inv.status = new_status.lower()
        inv.updated_at = datetime.utcnow()
        db.commit()
        return f"Invoice {invoice_id} for {inv.customer_name} updated to status '{new_status}'."
    finally:
        db.close()
