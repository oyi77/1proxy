import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Get project root
BASE_DIR = Path(__file__).parent.parent.parent

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "1proxy"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # URLs
    API_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    
    # OAuth
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/1proxy.db"
    
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
