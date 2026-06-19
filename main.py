from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.core.config import settings
from src.core.middleware import RequestLoggingMiddleware
from src.core.exceptions import register_exception_handlers
from src.database.init_db import create_all_tables

from src.api.v1 import test_api, chat
from src.api.v1 import agent, invoices, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup tasks before accepting requests."""
    create_all_tables()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=(
            "A full **Agentic Business Automation Platform** powered by LangGraph ReAct agents, "
            "Groq LLM, and LangChain tools. Automate invoice management, analytics, and email "
            "workflows through natural-language task instructions."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Exception handlers
    register_exception_handlers(app)

    # Existing routers
    app.include_router(chat.app)
    app.include_router(test_api.app)

    # New routers
    app.include_router(agent.app)
    app.include_router(invoices.app)
    app.include_router(analytics.app)

    return app


app = create_app()