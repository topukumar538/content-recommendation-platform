from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./app.db"
    SECRET_KEY: str = "super-secret-key-change-this-in-production-12345"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    LOGIN_EXPIRE_TIME: int = 7
    OTP_EXPIRE_MIN: int = 10
    GMAIL_USER: str = "example@gmail.com"
    GMAIL_PASSWORD: str = "dummy-password"
    ALLOWED_ORIGINS: str = "http://localhost:8000"
    REQUIRE_DB_SSL: bool = False

    DEMO_MODE: bool = False
    REQUIRE_DB_SSL: bool = False

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        extra="ignore"
    )

settings = Settings()  # type: ignore