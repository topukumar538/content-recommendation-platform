import os

os.environ["TESTING"] = "true"
os.environ["DEMO_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest
from fastapi.testclient import TestClient

from database import Base, engine, get_db, SessionLocal
from main import app


def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Direct DB access for test setup. Always closed, unlike next(get_db())."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()