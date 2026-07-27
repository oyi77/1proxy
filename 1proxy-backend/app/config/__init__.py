import os
import secrets
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent.parent

# Persistent secret key: read from file or generate & write on first run.
_SECRET_KEY_FILE = BASE_DIR / ".secret_key"
if os.getenv("SECRET_KEY"):
    _DEFAULT_SECRET = os.environ["SECRET_KEY"]
elif _SECRET_KEY_FILE.exists():
    _DEFAULT_SECRET = _SECRET_KEY_FILE.read_text().strip()
else:
    _DEFAULT_SECRET = secrets.token_urlsafe(32)
    _SECRET_KEY_FILE.write_text(_DEFAULT_SECRET)


class Settings(BaseSettings):
    PROJECT_NAME: str = "1proxy"
    API_V1_STR: str = "/api/v1"

    SECRET_KEY: str = _DEFAULT_SECRET

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Public URLs. Production runs with the frontend on GitHub Pages and the
    # backend on Railway. Railway can provide RAILWAY_PUBLIC_DOMAIN; API_URL and
    # FRONTEND_URL remain explicit overrides for local/dev and custom domains.
    API_URL: str = os.getenv(
        "API_URL",
        f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN')}"
        if os.getenv("RAILWAY_PUBLIC_DOMAIN")
        else "http://localhost:8000",
    )
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    # Optional base path when frontend is hosted under a subpath (e.g. GitHub Pages)
    FRONTEND_BASE_PATH: str = os.getenv("FRONTEND_BASE_PATH", "")

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
