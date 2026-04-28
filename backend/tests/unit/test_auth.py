import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from services import auth_service
from models import User


# ── helpers ──────────────────────────────────────────────────

def make_user(is_active=True, is_blocked=False, password="hashed"):
    user = MagicMock(spec=User)
    user.id         = 1
    user.email      = "test@test.com"
    user.username   = "testuser"
    user.role       = "user"
    user.is_active  = is_active
    user.is_blocked = is_blocked
    user.password   = password
    return user


def make_db(user=None):
    """Mock DB session"""
    db = MagicMock()
    query_mock = db.query.return_value
    query_mock.filter.return_value.first.return_value = user
    return db


# ── login tests ───────────────────────────────────────────────

def test_login_user_not_found():
    db = make_db(user=None)
    from schemas.auth import LoginRequest
    data = LoginRequest(email="notfound@test.com", password="123456")
    with pytest.raises(ValueError, match="Email not found"):
        auth_service.login(data, db)


def test_login_wrong_password():
    user = make_user()
    db   = make_db(user=user)
    from schemas.auth import LoginRequest
    data = LoginRequest(email="test@test.com", password="wrongpassword")
    with patch("services.auth_service.verify_password", return_value=False):
        with pytest.raises(ValueError, match="Wrong password"):
            auth_service.login(data, db)


def test_login_unverified_user():
    user = make_user(is_active=False)
    db   = make_db(user=user)
    from schemas.auth import LoginRequest
    data = LoginRequest(email="test@test.com", password="123456")
    with patch("services.auth_service.verify_password", return_value=True):
        with pytest.raises(ValueError, match="verify your email"):
            auth_service.login(data, db)


def test_login_blocked_user():
    user = make_user(is_blocked=True)
    db   = make_db(user=user)
    from schemas.auth import LoginRequest
    data = LoginRequest(email="test@test.com", password="123456")
    with patch("services.auth_service.verify_password", return_value=True):
        with pytest.raises(ValueError, match="blocked"):
            auth_service.login(data, db)


def test_login_success():
    user = make_user()
    db   = make_db(user=user)
    from schemas.auth import LoginRequest
    data = LoginRequest(email="test@test.com", password="123456")
    with patch("services.auth_service.verify_password", return_value=True):
        with patch("services.auth_service.create_access_token", return_value="token123"):
            result = auth_service.login(data, db)
            assert result["token"] == "token123"
            assert result["role"] == "user"


# ── signup tests ──────────────────────────────────────────────

def test_signup_email_already_registered():
    user = make_user(is_active=True)
    db   = make_db(user=user)
    from schemas.auth import SignupRequest
    data = SignupRequest(username="test", email="test@test.com", password="123456")
    with pytest.raises(ValueError, match="already registered"):
        auth_service.signup(data, db)


def test_signup_password_too_short():
    db = make_db(user=None)
    from schemas.auth import SignupRequest
    data = SignupRequest(username="test", email="new@test.com", password="123")
    with pytest.raises(ValueError, match="6 characters"):
        auth_service.signup(data, db)


# ── password tests ────────────────────────────────────────────

def test_reset_password_mismatch():
    db = make_db()
    with pytest.raises(ValueError, match="do not match"):
        auth_service.reset_password(
            "test@test.com", "123456", "newpass1", "newpass2", db
        )

def test_reset_password_too_short():
    db = make_db()
    with pytest.raises(ValueError, match="6 characters"):
        auth_service.reset_password(
            "test@test.com", "123456", "abc", "abc", db
        )

def test_change_password_mismatch():
    user = make_user()
    db   = make_db()
    with pytest.raises(ValueError, match="do not match"):
        auth_service.change_password(user, "123456", "newpass1", "newpass2", db)