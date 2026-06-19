import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"), override=True)


class Settings(BaseSettings):
    PROJECT_NAME: str = "Agentic Business Automation"
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    CHAT_MODEL: str = os.getenv("CHAT_MODEL", "llama-3.3-70b-versatile")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./agentic_business.db")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # SMTP — leave blank to use dry-run mode
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "noreply@agenticbiz.com")

    model_config = ConfigDict(env_file=".env", extra="allow")


settings = Settings()