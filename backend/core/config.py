from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_DAYS: int
    LOGIN_EXPIRE_TIME: int
    OTP_EXPIRE_MIN: int
    GMAIL_USER: str
    GMAIL_PASSWORD: str
    ALLOWED_ORIGINS: str = "http://localhost:8000"  # ← add this

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        extra="ignore"
    )

settings = Settings()  # type: ignore