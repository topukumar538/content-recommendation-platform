from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from core.dependencies import get_current_active_user
from core.config import settings
from database import get_db
from schemas.auth import (
    SignupRequest, LoginRequest, VerifyOTPRequest, ResendOTPRequest,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
)
from services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/signup")
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    try:
        return auth_service.signup(data, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/resend-otp")
def resend_otp(data: ResendOTPRequest, db: Session = Depends(get_db)):
    try:
        return auth_service.resend_otp(data.email, data.purpose, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify-otp")
def verify_otp(data: VerifyOTPRequest, db: Session = Depends(get_db)):
    try:
        return auth_service.verify_signup_otp(data.email, data.code, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    try:
        result = auth_service.login(data, db)
        response.set_cookie(
            key="token",
            value=result["token"],
            httponly=True,
            max_age=settings.LOGIN_EXPIRE_TIME * 24 * 60 * 60,
            samesite="lax"
        )
        return {"message": "Login successful", "role": result["role"]}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("token")
    return {"message": "Logged out successfully"}

@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    try:
        return auth_service.forgot_password(data.email, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        return auth_service.reset_password(
            data.email, data.code, data.new_password, data.confirm_password, db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/request-change-password-otp")
def request_change_password_otp(
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        return auth_service.request_change_password_otp(user, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user)
):
    try:
        return auth_service.change_password(
            user, data.code, data.new_password, data.confirm_password, db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/me")
def get_me(user=Depends(get_current_active_user)):
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role
    }