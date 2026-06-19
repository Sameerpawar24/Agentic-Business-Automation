from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from src.database.base import get_db
from src.services.invoice_service import InvoiceService
from typing import Optional
from datetime import datetime

app = APIRouter(prefix="/invoices", tags=["Invoices"])

invoice_service = InvoiceService()


# ── Schemas ────────────────────────────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    customer_name: str
    customer_email: str
    amount: float
    due_date: Optional[datetime] = None
    status: Optional[str] = "unpaid"
    notes: Optional[str] = None


class InvoiceUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None


def _invoice_to_dict(inv) -> dict:
    return {
        "id": inv.id,
        "customer_name": inv.customer_name,
        "customer_email": inv.customer_email,
        "amount": inv.amount,
        "due_date": inv.due_date.isoformat() if inv.due_date else None,
        "status": inv.status,
        "notes": inv.notes,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
    }


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/", summary="List all invoices")
async def list_invoices(status: Optional[str] = None, db: Session = Depends(get_db)):
    """Return all invoices, optionally filtered by status (paid | unpaid | overdue)."""
    invoices = invoice_service.get_all(db, status=status)
    return [_invoice_to_dict(inv) for inv in invoices]


@app.post("/", summary="Create a new invoice")
async def create_invoice(data: InvoiceCreate, db: Session = Depends(get_db)):
    """Create a new invoice record."""
    inv = invoice_service.create(db, data.model_dump())
    return _invoice_to_dict(inv)


@app.get("/{invoice_id}", summary="Get invoice by ID")
async def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Retrieve a single invoice by its integer ID."""
    inv = invoice_service.get_by_id(db, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found.")
    return _invoice_to_dict(inv)


@app.put("/{invoice_id}", summary="Update an invoice")
async def update_invoice(invoice_id: int, data: InvoiceUpdate, db: Session = Depends(get_db)):
    """Update invoice fields. Only provided fields will be changed."""
    inv = invoice_service.update(db, invoice_id, data.model_dump(exclude_none=True))
    if not inv:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found.")
    return _invoice_to_dict(inv)


@app.post("/seed", summary="Seed 10 demo invoices")
async def seed_invoices(db: Session = Depends(get_db)):
    """
    Insert 10 realistic demo invoices (Acme Corp, Stark Industries, etc.).
    Safe to call multiple times — skips if invoices already exist.
    """
    count = invoice_service.seed_demo(db)
    if count == 0:
        return {"message": "Invoices already exist — nothing seeded.", "seeded": 0}
    return {"message": f"Successfully seeded {count} demo invoices.", "seeded": count}
