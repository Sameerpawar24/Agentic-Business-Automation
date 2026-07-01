import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from src.core.config import settings
from src.core.middleware import RequestLoggingMiddleware
from src.core.exceptions import register_exception_handlers
from src.database.init_db import create_all_tables

from src.api.v1 import test_api, chat
from src.api.v1 import agent, invoices, analytics, logs

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"


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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)

    app.include_router(chat.app)
    app.include_router(test_api.app)
    app.include_router(agent.app)
    app.include_router(invoices.app)
    app.include_router(analytics.app)
    app.include_router(logs.app)

    if FRONTEND_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")

        @app.get("/")
        async def serve_ui():
            return FileResponse(FRONTEND_DIR / "index.html")

    return app


app = create_app()
