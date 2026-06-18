from fastapi import FastAPI
from src.core.config import settings
from src.api.v1 import test_api

def create_app():
    app = FastAPI(title=settings.PROJECT_NAME)

   
    app.include_router(test_api.app)

    return app

app = create_app()