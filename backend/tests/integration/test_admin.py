import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from database import get_db
from models import User


# ── mock email globally ───────────────────────────────────────
@pytest.fixture(autouse=True)
def mock_email():
    with patch("routes.auth.send_otp_email"):
        yield


# ── helpers ───────────────────────────────────────────────────
def create_user_and_login(client, email="user@test.com", password="123456"):
    client.post("/auth/signup", json={
        "username": "testuser",
        "email": email,
        "password": password
    })
    db = next(client.app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.email == email).first()
    user.is_active = True
    db.commit()
    res = client.post("/auth/login", json={"email": email, "password": password})
    return res.cookies, user.id


def create_admin_and_login(client, email="admin@test.com", password="123456"):
    client.post("/auth/signup", json={
        "username": "admin",
        "email": email,
        "password": password
    })
    db = next(client.app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.email == email).first()
    user.is_active = True
    user.role = "admin"
    db.commit()
    res = client.post("/auth/login", json={"email": email, "password": password})
    return res.cookies


# ── tests ─────────────────────────────────────────────────────

def test_admin_can_get_users(client):
    """Admin can access user list"""
    admin_cookies = create_admin_and_login(client)
    res = client.get("/admin/users", cookies=admin_cookies)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_non_admin_cannot_access_admin_routes(client):
    """Regular user cannot access admin routes"""
    user_cookies, _ = create_user_and_login(client)
    res = client.get("/admin/users", cookies=user_cookies)
    assert res.status_code == 403


def test_admin_block_user(client):
    """Admin can block a user"""
    admin_cookies = create_admin_and_login(client)
    user_cookies, user_id = create_user_and_login(client)

    # block the user
    res = client.patch(f"/admin/users/{user_id}/block", cookies=admin_cookies)
    assert res.status_code == 200
    assert "blocked" in res.json()["message"]


def test_blocked_user_cannot_access_feed(client):
    """Blocked user is denied access to feed"""
    admin_cookies = create_admin_and_login(client)
    user_cookies, user_id = create_user_and_login(client)

    # user can access feed before block
    res = client.get("/feed", cookies=user_cookies)
    assert res.status_code == 200

    # admin blocks user
    client.patch(f"/admin/users/{user_id}/block", cookies=admin_cookies)

    # user cannot access feed after block
    res = client.get("/feed", cookies=user_cookies)
    assert res.status_code == 403


def test_admin_unblock_user(client):
    """Admin can unblock a user"""
    admin_cookies = create_admin_and_login(client)
    user_cookies, user_id = create_user_and_login(client)

    # block
    client.patch(f"/admin/users/{user_id}/block", cookies=admin_cookies)

    # unblock
    res = client.patch(f"/admin/users/{user_id}/block", cookies=admin_cookies)
    assert res.status_code == 200
    assert "unblocked" in res.json()["message"]


def test_unblocked_user_can_access_feed(client):
    """Unblocked user can access feed again"""
    admin_cookies = create_admin_and_login(client)
    user_cookies, user_id = create_user_and_login(client)

    # block then unblock
    client.patch(f"/admin/users/{user_id}/block", cookies=admin_cookies)
    client.patch(f"/admin/users/{user_id}/block", cookies=admin_cookies)

    # user can access feed again
    res = client.get("/feed", cookies=user_cookies)
    assert res.status_code == 200


def test_cannot_block_admin(client):
    """Admin cannot block another admin"""
    admin_cookies = create_admin_and_login(client, email="admin@test.com")
    admin2_cookies, admin2_id = create_user_and_login(client, email="admin2@test.com")

    # promote second user to admin
    db = next(client.app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.email == "admin2@test.com").first()
    user.role = "admin"
    db.commit()

    # try to block admin2
    res = client.patch(f"/admin/users/{admin2_id}/block", cookies=admin_cookies)
    assert res.status_code == 400