from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database.base import get_db
from src.models.invoice import Invoice
from src.models.workflow_run import WorkflowRun
from src.models.tool_call_log import ToolCallLog
from datetime import datetime

app = APIRouter(prefix="/analytics", tags=["Analytics"])


@app.get("/summary", summary="Full business analytics summary")
async def analytics_summary(db: Session = Depends(get_db)):
    """
    Returns a complete dashboard summary:
    - Invoice counts and totals by status
    - Total revenue collected (paid)
    - Total outstanding (unpaid + overdue)
    - Workflow run statistics
    - Tool call statistics
    """
    # Invoice analytics
    invoice_rows = (
        db.query(Invoice.status, func.count(Invoice.id), func.sum(Invoice.amount))
        .group_by(Invoice.status)
        .all()
    )
    invoice_stats = {}
    total_revenue = 0.0
    total_outstanding = 0.0
    for status, count, total in invoice_rows:
        amt = round(total or 0, 2)
        invoice_stats[status] = {"count": count, "total_amount": amt}
        if status == "paid":
            total_revenue += amt
        else:
            total_outstanding += amt

    # Top 5 customers
    top_customers = (
        db.query(Invoice.customer_name, func.sum(Invoice.amount).label("total"))
        .group_by(Invoice.customer_name)
        .order_by(func.sum(Invoice.amount).desc())
        .limit(5)
        .all()
    )

    # Workflow run stats
    run_stats = (
        db.query(WorkflowRun.status, func.count(WorkflowRun.id))
        .group_by(WorkflowRun.status)
        .all()
    )

    # Tool call stats
    tool_stats = (
        db.query(ToolCallLog.tool_name, func.count(ToolCallLog.id))
        .group_by(ToolCallLog.tool_name)
        .order_by(func.count(ToolCallLog.id).desc())
        .all()
    )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "invoices": {
            "by_status": invoice_stats,
            "total_revenue_collected": round(total_revenue, 2),
            "total_outstanding": round(total_outstanding, 2),
        },
        "top_customers": [
            {"customer": r[0], "total_amount": round(r[1] or 0, 2)}
            for r in top_customers
        ],
        "workflow_runs": {r[0]: r[1] for r in run_stats},
        "tool_usage": {r[0]: r[1] for r in tool_stats},
    }


@app.get("/overdue", summary="List overdue invoices")
async def overdue_invoices(db: Session = Depends(get_db)):
    """
    Returns all invoices that are either:
    - Status = 'overdue', or
    - Status = 'unpaid' with due_date in the past
    """
    now = datetime.utcnow()
    overdue = (
        db.query(Invoice)
        .filter(
            (Invoice.status == "overdue")
            | ((Invoice.status == "unpaid") & (Invoice.due_date < now))
        )
        .order_by(Invoice.due_date.asc())
        .all()
    )
    return {
        "count": len(overdue),
        "total_overdue_amount": round(sum(inv.amount for inv in overdue), 2),
        "invoices": [
            {
                "id": inv.id,
                "customer_name": inv.customer_name,
                "customer_email": inv.customer_email,
                "amount": inv.amount,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "status": inv.status,
                "days_overdue": (now - inv.due_date).days if inv.due_date and inv.due_date < now else 0,
            }
            for inv in overdue
        ],
    }


@app.get("/summary/download", summary="Download full business report as text file")
async def download_analytics_summary(db: Session = Depends(get_db)):
    """
    Returns the complete dashboard summary formatted as a downloadable plain text (.txt) file.
    """
    data = await analytics_summary(db)
    
    # Format plain text report
    lines = [
        "=========================================",
        "      BUSINESS ANALYTICS SUMMARY",
        "=========================================",
        f"Generated at: {data.get('generated_at')} UTC",
        "",
        "INVOICE STATUS SUMMARY",
        "-----------------------------------------",
    ]
    
    invoices_by_status = data.get("invoices", {}).get("by_status", {})
    if not invoices_by_status:
        lines.append("(No invoices found)")
    for status, stats in invoices_by_status.items():
        lines.append(f"- {status.upper()}:")
        lines.append(f"  * Count: {stats.get('count', 0)}")
        lines.append(f"  * Total Amount: ${stats.get('total_amount', 0.0):,.2f}")
    
    lines.extend([
        "",
        "FINANCIAL TOTALS",
        "-----------------------------------------",
        f"- Total Revenue Collected (Paid): ${data.get('invoices', {}).get('total_revenue_collected', 0.0):,.2f}",
        f"- Total Outstanding (Unpaid/Overdue): ${data.get('invoices', {}).get('total_outstanding', 0.0):,.2f}",
        "",
        "TOP 5 CUSTOMERS",
        "-----------------------------------------",
    ])
    
    top_customers = data.get("top_customers", [])
    if not top_customers:
        lines.append("(No customer data)")
    for idx, cust in enumerate(top_customers, start=1):
        lines.append(f"{idx}. {cust.get('customer', 'Unknown')}: ${cust.get('total_amount', 0.0):,.2f}")
        
    lines.extend([
        "",
        "WORKFLOW RUN STATISTICS",
        "-----------------------------------------",
    ])
    
    workflow_runs = data.get("workflow_runs", {})
    if not workflow_runs:
        lines.append("(No workflow runs recorded)")
    for status, count in workflow_runs.items():
        lines.append(f"- {status.upper()}: {count} run(s)")
        
    lines.extend([
        "",
        "TOOL USAGE STATISTICS",
        "-----------------------------------------",
    ])
    
    tool_usage = data.get("tool_usage", {})
    if not tool_usage:
        lines.append("(No tool calls recorded)")
    for tool_name, count in tool_usage.items():
        lines.append(f"- {tool_name}: {count} call(s)")
        
    lines.append("=========================================")
    
    report_content = "\n".join(lines)
    
    return Response(
        content=report_content,
        media_type="text/plain",
        headers={
            "Content-Disposition": 'attachment; filename="business_summary_report.txt"'
        }
    )

