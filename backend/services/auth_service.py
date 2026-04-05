from sqlalchemy.orm import Session
from models import User
from schemas.auth import SignupRequest, LoginRequest
from core.security import hash_password, verify_password, create_access_token
from services.otp_service import create_otp, verify_otp

def signup(data: SignupRequest, db: Session):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            db.commit()
            return {"message": "Account activated. Please login."}
        raise ValueError("Email already registered")
    if len(data.password) < 6:
        raise ValueError("Password must be at least 6 characters")
    user = User(
        username=data.username,
        email=data.email,
        password=hash_password(data.password),
        is_active=True  # activate directly
    )
    db.add(user)
    db.commit()
    return {"message": "Account created. Please login."}

def forgot_password(email: str, db: Session):
    raise ValueError("Password reset not available in demo version. Contact admin.")

def request_change_password_otp(user: User, db: Session):
    raise ValueError("OTP not available in demo version.")

def change_password(user, code, new_password, confirm_password, db):
    raise ValueError("Change password not available in demo version.")

def resend_otp(email: str, purpose: str, db: Session):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise ValueError("Email not found")
    if purpose == "signup" and user.is_active:
        raise ValueError("Account already verified")
    create_otp(email, purpose, db)
    return {"message": "OTP resent successfully"}

def verify_signup_otp(email: str, code: str, db: Session):
    success = verify_otp(email, code, "signup", db)
    if not success:
        raise ValueError("Invalid or expired OTP")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise ValueError("User not found")
    user.is_active = True
    db.commit()
    return {"message": "Account verified successfully. Please login."}

def login(data: LoginRequest, db: Session):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise ValueError("Email not found")
    if not verify_password(data.password, user.password):
        raise ValueError("Wrong password")
    if not user.is_active:
        raise ValueError("Please verify your email first")
    if user.is_blocked:
        raise ValueError("Your account has been blocked. Contact admin.")
    token = create_access_token({
        "user_id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role
    })
    return {"token": token, "role": user.role}


def reset_password(email: str, code: str, new_password: str, confirm_password: str, db: Session):
    if new_password != confirm_password:
        raise ValueError("Passwords do not match")
    if len(new_password) < 6:
        raise ValueError("Password must be at least 6 characters")
    success = verify_otp(email, code, "forgot_password", db)
    if not success:
        raise ValueError("Invalid or expired OTP")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise ValueError("User not found")
    user.password = hash_password(new_password)
    db.commit()
    return {"message": "Password reset successfully. Please login."}

