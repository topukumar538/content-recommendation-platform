from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_DAYS: int
    GMAIL_USER: str
    GMAIL_PASSWORD: str
    OTP_EXPIRE_MIN: int
    LOGIN_EXPIRE_TIME: int

    class Config:
        env_file = str(BASE_DIR / ".env")

settings = Settings()  # type: ignore