from langchain_core.tools import tool
from sqlalchemy import func
from src.database.base import SessionLocal
from src.models.invoice import Invoice
from datetime import datetime
import json


def _get_db():
    return SessionLocal()


@tool
def generate_report(report_type: str) -> str:
    """
    Generate a business analytics report.
    Args:
        report_type: Type of report to generate. Options:
            - 'revenue_summary'  — total revenue by status
            - 'overdue_stats'    — count and total amount of overdue invoices
            - 'top_customers'    — top 5 customers by total invoice amount
            - 'full_summary'     — all of the above combined
    Returns:
        JSON string with report data.
    """
    db = _get_db()
    try:
        rtype = report_type.lower().strip()

        if rtype == "revenue_summary":
            rows = (
                db.query(Invoice.status, func.count(Invoice.id), func.sum(Invoice.amount))
                .group_by(Invoice.status)
                .all()
            )
            data = {
                row[0]: {"count": row[1], "total_amount": round(row[2] or 0, 2)}
                for row in rows
            }
            return json.dumps({"report": "revenue_summary", "data": data})

        elif rtype == "overdue_stats":
            now = datetime.utcnow()
            # Auto-compute overdue: unpaid invoices past due_date
            overdue = (
                db.query(Invoice)
                .filter(Invoice.status == "unpaid", Invoice.due_date < now)
                .all()
            )
            return json.dumps({
                "report": "overdue_stats",
                "count": len(overdue),
                "total_overdue_amount": round(sum(inv.amount for inv in overdue), 2),
                "invoices": [
                    {"id": inv.id, "customer": inv.customer_name, "amount": inv.amount,
                     "due_date": inv.due_date.isoformat()}
                    for inv in overdue
                ],
            })

        elif rtype == "top_customers":
            rows = (
                db.query(Invoice.customer_name, func.sum(Invoice.amount).label("total"))
                .group_by(Invoice.customer_name)
                .order_by(func.sum(Invoice.amount).desc())
                .limit(5)
                .all()
            )
            return json.dumps({
                "report": "top_customers",
                "data": [{"customer": r[0], "total_amount": round(r[1] or 0, 2)} for r in rows],
            })

        elif rtype == "full_summary":
            # Combine all reports
            revenue = json.loads(generate_report.invoke({"report_type": "revenue_summary"}))
            overdue = json.loads(generate_report.invoke({"report_type": "overdue_stats"}))
            top = json.loads(generate_report.invoke({"report_type": "top_customers"}))
            return json.dumps({
                "report": "full_summary",
                "revenue_summary": revenue["data"],
                "overdue_stats": {k: v for k, v in overdue.items() if k != "report"},
                "top_customers": top["data"],
            })

        else:
            return json.dumps({
                "error": f"Unknown report_type '{report_type}'. "
                         "Valid options: revenue_summary, overdue_stats, top_customers, full_summary."
            })
    finally:
        db.close()
