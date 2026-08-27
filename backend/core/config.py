from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# config.py lives at <repo>/backend/core/config.py
#   parents[0] = backend/core
#   parents[1] = backend
#   parents[2] = <repo root>  ← .env lives here, next to docker-compose.yml
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    LOGIN_EXPIRE_TIME: int = 7
    OTP_EXPIRE_MIN: int = 10
    GMAIL_USER: str = "example@gmail.com"
    GMAIL_PASSWORD: str = "dummy-password"
    ALLOWED_ORIGINS: str = "http://localhost:8000"
    REQUIRE_DB_SSL: bool = False

    DEMO_MODE: bool = False
    TESTING: bool = False

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        extra="ignore"
    )


settings = Settings()  # type: ignore