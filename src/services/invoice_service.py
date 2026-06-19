import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from src.models.invoice import Invoice

logger = logging.getLogger("agentic.invoice_service")

DEMO_INVOICES = [
    {"customer_name": "Acme Corp",        "customer_email": "billing@acme.com",        "amount": 4500.00,  "status": "unpaid",  "days_offset": -5},
    {"customer_name": "Globex Inc",        "customer_email": "accounts@globex.com",      "amount": 12000.00, "status": "overdue", "days_offset": -30},
    {"customer_name": "Initech Solutions", "customer_email": "finance@initech.com",      "amount": 850.00,   "status": "paid",    "days_offset": 10},
    {"customer_name": "Umbrella LLC",      "customer_email": "pay@umbrella.com",          "amount": 7300.00,  "status": "unpaid",  "days_offset": -2},
    {"customer_name": "Stark Industries",  "customer_email": "tony@stark.com",            "amount": 99000.00, "status": "paid",    "days_offset": 15},
    {"customer_name": "Wayne Enterprises", "customer_email": "bruce@wayne.com",           "amount": 25000.00, "status": "overdue", "days_offset": -45},
    {"customer_name": "Oscorp",            "customer_email": "norman@oscorp.com",         "amount": 3200.00,  "status": "unpaid",  "days_offset": -1},
    {"customer_name": "Pied Piper",        "customer_email": "richard@piedpiper.com",     "amount": 1100.00,  "status": "paid",    "days_offset": 7},
    {"customer_name": "Hooli Tech",        "customer_email": "accounts@hooli.com",        "amount": 5500.00,  "status": "overdue", "days_offset": -60},
    {"customer_name": "Dunder Mifflin",    "customer_email": "michael@dundermifflin.com", "amount": 640.00,   "status": "unpaid",  "days_offset": -3},
]


class InvoiceService:
    """CRUD operations and seeding logic for the Invoice model."""

    def get_all(self, db: Session, status: Optional[str] = None) -> List[Invoice]:
        query = db.query(Invoice)
        if status:
            query = query.filter(Invoice.status == status.lower())
        return query.order_by(Invoice.created_at.desc()).all()

    def get_by_id(self, db: Session, invoice_id: int) -> Optional[Invoice]:
        return db.query(Invoice).filter(Invoice.id == invoice_id).first()

    def create(self, db: Session, data: dict) -> Invoice:
        inv = Invoice(
            customer_name=data["customer_name"],
            customer_email=data["customer_email"],
            amount=data["amount"],
            due_date=data.get("due_date", datetime.utcnow() + timedelta(days=30)),
            status=data.get("status", "unpaid"),
            notes=data.get("notes"),
        )
        db.add(inv)
        db.commit()
        db.refresh(inv)
        return inv

    def update(self, db: Session, invoice_id: int, data: dict) -> Optional[Invoice]:
        inv = self.get_by_id(db, invoice_id)
        if not inv:
            return None
        for field in ("customer_name", "customer_email", "amount", "status", "notes", "due_date"):
            if field in data:
                setattr(inv, field, data[field])
        inv.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(inv)
        return inv

    def seed_demo(self, db: Session) -> int:
        """Insert 10 demo invoices. Skips if data already exists."""
        existing = db.query(Invoice).count()
        if existing > 0:
            logger.info("Skipping seed — %d invoices already exist.", existing)
            return 0
        now = datetime.utcnow()
        for item in DEMO_INVOICES:
            inv = Invoice(
                customer_name=item["customer_name"],
                customer_email=item["customer_email"],
                amount=item["amount"],
                due_date=now + timedelta(days=item["days_offset"]),
                status=item["status"],
            )
            db.add(inv)
        db.commit()
        logger.info("Seeded %d demo invoices.", len(DEMO_INVOICES))
        return len(DEMO_INVOICES)
