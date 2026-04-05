from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from jose import JWTError
from core.security import decode_token
from database import get_db
from models import User

def get_current_user(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")
    try:
        payload = decode_token(token)
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_current_active_user(request: Request, db: Session = Depends(get_db)):
    payload = get_current_user(request)
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="Your account has been blocked")
    return user

def admin_only(request: Request):
    payload = get_current_user(request)
    if payload["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return payload