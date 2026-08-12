import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from database import get_db
from models import User
# ── helpers ──────────────────────────────────────────────────

# mock email globally — never send real emails during tests
@pytest.fixture(autouse=True)
def mock_email():
    with patch("routes.auth.send_otp_email"):
        yield

def register_and_login(client, email="user@test.com", password="123456"):
    """Create a user and return auth cookies"""
    # signup
    client.post("/auth/signup", json={
        "username": "testuser",
        "email": email,
        "password": password
    })

    # manually verify — bypass OTP for testing
    from sqlalchemy.orm import Session
    from database import get_db
    from models import User
    db = next(client.app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.is_active = True
        db.commit()

    # login
    res = client.post("/auth/login", json={
        "email": email,
        "password": password
    })
    return res.cookies


def create_category(client, admin_cookies, name="Technology"):
    res = client.post("/categories",
        json={"name": name},
        cookies=admin_cookies
    )
    return res.json()["id"]


def create_post(client, admin_cookies, category_id):
    res = client.post("/feed", json={
        "title": "Test Post",
        "content": "This is test content for the post.",
        "category_id": category_id
    }, cookies=admin_cookies)
    return res.json()["id"]


def make_admin(client, email):
    """Promote user to admin"""
    from models import User
    db = next(client.app.dependency_overrides[client.app.dependency_overrides.__class__]())
    pass


# ── tests ─────────────────────────────────────────────────────

def test_signup_and_login(client):
    """User can sign up and login successfully"""
    # signup
    res = client.post("/auth/signup", json={
        "username": "testuser",
        "email": "user@test.com",
        "password": "123456"
    })
    assert res.status_code == 200

    # manually activate
    from models import User
    db = next(client.app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.email == "user@test.com").first()
    user.is_active = True
    db.commit()

    # login
    res = client.post("/auth/login", json={
        "email": "user@test.com",
        "password": "123456"
    })
    assert res.status_code == 200
    assert res.json()["role"] == "user"


def test_feed_requires_auth(client):
    """Feed endpoint should reject unauthenticated requests"""
    res = client.get("/feed")
    assert res.status_code == 401


def test_login_wrong_password(client):
    """Login with wrong password returns 401"""
    # create user first
    client.post("/auth/signup", json={
        "username": "testuser",
        "email": "user@test.com",
        "password": "123456"
    })
    res = client.post("/auth/login", json={
        "email": "user@test.com",
        "password": "wrongpassword"
    })
    assert res.status_code == 401


def test_me_endpoint(client):
    """Logged in user can access /auth/me"""
    cookies = register_and_login(client)
    res = client.get("/auth/me", cookies=cookies)
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "user@test.com"
    assert data["role"] == "user"


def test_feed_returns_paginated_response(client):
    """Feed returns paginated response shape"""
    cookies = register_and_login(client)
    res = client.get("/feed", cookies=cookies)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "pages" in data


def test_logout(client):
    """Logout clears the session"""
    cookies = register_and_login(client)

    # verify logged in
    res = client.get("/auth/me", cookies=cookies)
    assert res.status_code == 200

    # logout
    res = client.post("/auth/logout", cookies=cookies)
    assert res.status_code == 200
    assert res.json()["message"] == "Logged out successfully"


def test_duplicate_signup(client):
    """Signing up with same email twice returns error"""
    client.post("/auth/signup", json={
        "username": "testuser",
        "email": "user@test.com",
        "password": "123456"
    })
    # manually activate
    from models import User
    db = next(client.app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.email == "user@test.com").first()
    user.is_active = True
    db.commit()

    # try signup again
    res = client.post("/auth/signup", json={
        "username": "testuser2",
        "email": "user@test.com",
        "password": "123456"
    })
    assert res.status_code == 400