import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from dotenv import load_dotenv
load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = "AGENTIC BUSINESS AUTOMATION"
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    #CHAT_MODEL: str = os.getenv("CHAT_MODEL")


    model_config = ConfigDict(env_file=".env", extra="allow")



settings = Settings()