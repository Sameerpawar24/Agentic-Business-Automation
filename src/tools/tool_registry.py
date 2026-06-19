"""
Central tool registry — all LangChain tools available to the agent.
Import ALL_TOOLS wherever you need the full tool list.
"""
from src.tools.db_tool import get_invoices, get_invoice_by_id, update_invoice_status
from src.tools.email_tool import send_email
from src.tools.search_tool import search_documents
from src.tools.analytics_tool import generate_report

ALL_TOOLS = [
    get_invoices,
    get_invoice_by_id,
    update_invoice_status,
    send_email,
    search_documents,
    generate_report,
]

TOOL_MAP = {tool.name: tool for tool in ALL_TOOLS}
