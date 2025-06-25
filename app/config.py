# logistics_ai_project/app/config.py
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(dotenv_path=ENV_PATH)

class Settings(BaseSettings):
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    Maps_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY")
    FRONTEND_ORIGIN: str = "*"
    FUEL_COST_PER_KM: float = 27   

    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ENV_PATH # Tell Pydantic where to load .env from
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignore extra fields from .env if any

settings = Settings()

import openai
openai.api_key = settings.OPENAI_API_KEY