from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from core.config import settings

if settings.DATABASE_URL.startswith("postgresql"):
    connect_args = {}
    if settings.REQUIRE_DB_SSL and "sslmode" not in settings.DATABASE_URL:
        connect_args["sslmode"] = "require"   # managed Postgres (Neon) requires SSL
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=5,
        max_overflow=5,
        pool_timeout=30,
        pool_recycle=300,   # Neon drops idle connections fast
        connect_args=connect_args
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()