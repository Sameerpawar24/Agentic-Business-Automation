from fastapi import Request
from fastapi.responses import JSONResponse


# ── Custom Exceptions ──────────────────────────────────────────────────────────

class AgentTimeoutError(Exception):
    """Raised when the agent exceeds the configured step or time limit."""
    pass


class ToolExecutionError(Exception):
    """Raised when a LangChain tool fails during execution."""
    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' failed: {message}")


class PlannerError(Exception):
    """Raised when the planner cannot decompose a task."""
    pass


class InvoiceNotFoundError(Exception):
    """Raised when an invoice with the given ID does not exist."""
    pass


# ── FastAPI Exception Handlers ─────────────────────────────────────────────────

async def agent_timeout_handler(request: Request, exc: AgentTimeoutError):
    return JSONResponse(
        status_code=504,
        content={"error": "Agent timeout", "detail": str(exc)},
    )


async def tool_execution_handler(request: Request, exc: ToolExecutionError):
    return JSONResponse(
        status_code=500,
        content={"error": "Tool execution failed", "tool": exc.tool_name, "detail": str(exc)},
    )


async def planner_error_handler(request: Request, exc: PlannerError):
    return JSONResponse(
        status_code=500,
        content={"error": "Planner failed", "detail": str(exc)},
    )


async def invoice_not_found_handler(request: Request, exc: InvoiceNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": "Invoice not found", "detail": str(exc)},
    )


def register_exception_handlers(app) -> None:
    """Register all custom exception handlers on the FastAPI app."""
    app.add_exception_handler(AgentTimeoutError, agent_timeout_handler)
    app.add_exception_handler(ToolExecutionError, tool_execution_handler)
    app.add_exception_handler(PlannerError, planner_error_handler)
    app.add_exception_handler(InvoiceNotFoundError, invoice_not_found_handler)
