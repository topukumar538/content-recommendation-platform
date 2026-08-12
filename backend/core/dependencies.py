from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from jose import JWTError
from core.security import decode_token
from database import get_db
from models import User


def get_current_user(request: Request):
    """
    Decodes the JWT only — no DB hit.

    Use this ONLY for routes that need nothing but the token payload. It cannot
    see revocations that happened after the token was issued (block, role change,
    deletion), so any route acting on behalf of a user should depend on
    get_current_active_user instead.
    """
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")
    try:
        payload = decode_token(token)
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_active_user(request: Request, db: Session = Depends(get_db)):
    """
    Decodes the JWT and re-checks the user against the DB on every request.

    Tokens live for 7 days, so without this a user blocked at minute 1 would keep
    full access for the remaining 7 days. Costs one indexed primary-key lookup.
    """
    payload = get_current_user(request)
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="Your account has been blocked")
    return user


def admin_only(request: Request, db: Session = Depends(get_db)):
    """
    Admin guard built on top of the DB-backed check.

    Role is read from the DB rather than the token, so a demotion or block takes
    effect immediately instead of when the token expires.
    """
    user = get_current_active_user(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return user