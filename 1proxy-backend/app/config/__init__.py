import os
import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Get project root
BASE_DIR = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "1proxy"
    API_V1_STR: str = "/api/v1"

    # SECRET_KEY: Auto-generate secure default for HuggingFace/development
    # IMPORTANT: Set this in production via environment variable!
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # URLs - Auto-detect HuggingFace Space environment
    API_URL: str = (
        os.getenv("SPACE_HOST", "").replace("https://", "https://")
        if os.getenv("SPACE_HOST")
        else "http://localhost:8000"
    )
    FRONTEND_URL: str = os.getenv("SPACE_HOST", "http://localhost:3000")

    # OAuth
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Admin Access - GitHub Repository Collaboration
    # Users with admin/owner/collaborator access to this repo get admin role
    GITHUB_REPO_OWNER: str = ""
    GITHUB_REPO_NAME: str = ""

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/1proxy.db"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
