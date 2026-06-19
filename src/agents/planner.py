import logging
from typing import List
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.config import settings

logger = logging.getLogger("agentic.planner")

PLANNER_SYSTEM_PROMPT = """You are a task planning assistant for a business automation system.
Given a user task, break it down into a concise ordered list of sub-steps that can each be 
accomplished by one of the following tools:
- get_invoices(status)         — fetch invoices filtered by status
- get_invoice_by_id(id)        — fetch a single invoice by ID
- update_invoice_status(id, status) — update an invoice status
- send_email(to, subject, body) — send an email to a customer
- search_documents(query)      — search invoices by keyword
- generate_report(report_type) — generate business analytics reports

Return ONLY a numbered list of steps. Be concise. Each step should be one action.
Example:
1. Get all unpaid invoices using get_invoices
2. For each unpaid invoice, send a reminder email using send_email
3. Generate a revenue summary report using generate_report
"""


class Planner:
    """
    Decomposes a high-level task into an ordered list of sub-steps
    using an LLM call before the agent executes.
    """

    def __init__(self):
        self.llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model=settings.CHAT_MODEL,
        )

    def plan(self, task: str) -> List[str]:
        """
        Given a task string, return a list of step strings.
        Falls back to [task] if the LLM call fails.
        """
        try:
            messages = [
                SystemMessage(content=PLANNER_SYSTEM_PROMPT),
                HumanMessage(content=f"Task: {task}"),
            ]
            response = self.llm.invoke(messages)
            raw = response.content.strip()
            steps = []
            for line in raw.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    # Strip leading number/dash/dot
                    cleaned = line.lstrip("0123456789.-) ").strip()
                    if cleaned:
                        steps.append(cleaned)
            if not steps:
                steps = [task]
            logger.info("Plan generated (%d steps): %s", len(steps), steps)
            return steps
        except Exception as exc:
            logger.warning("Planner failed, using raw task as plan: %s", exc)
            return [task]
