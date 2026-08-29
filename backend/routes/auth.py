from fastapi import APIRouter, Depends, HTTPException, Response, Request, BackgroundTasks
from sqlalchemy.orm import Session
from core.dependencies import get_current_active_user
from core.config import settings
from database import get_db
from services.otp_service import send_otp_email

from schemas.auth import (
    SignupRequest, LoginRequest, VerifyOTPRequest, ResendOTPRequest,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
)
from services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


def _is_secure(request: Request) -> bool:
    """
    Whether the browser reached us over HTTPS.

    Hugging Face terminates TLS at a proxy, so request.url.scheme is "http"
    inside the container even when the browser is on HTTPS. Trusting it
    directly sets samesite=lax on a cookie the hosted demo needs to send from
    inside an iframe, and the browser then withholds it on every request --
    the user appears logged out, or stuck as whoever they were before.

    x-forwarded-proto carries the original scheme. It can hold a chain
    ("https, http") when several proxies are involved; the first entry is
    the client-facing one.
    """
    proto = request.headers.get("x-forwarded-proto")
    if proto:
        return proto.split(",")[0].strip() == "https"
    return request.url.scheme == "https"


@router.post("/signup")
def signup(data: SignupRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        result = auth_service.signup(data, db)
        # add email to background — runs AFTER response is sent
        background_tasks.add_task(send_otp_email, result["email"], result["code"], result["purpose"])
        return {"message": result["message"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resend-otp")
def resend_otp(data: ResendOTPRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        result = auth_service.resend_otp(data.email, data.purpose, db)
        background_tasks.add_task(send_otp_email, result["email"], result["code"], result["purpose"])
        return {"message": result["message"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify-otp")
def verify_otp(data: VerifyOTPRequest, db: Session = Depends(get_db)):
    try:
        return auth_service.verify_signup_otp(data.email, data.code, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
def login(data: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    try:
        result = auth_service.login(data, db)
        is_secure = _is_secure(request)
        response.set_cookie(
            key="token",
            value=result["token"],
            httponly=True,
            max_age=settings.LOGIN_EXPIRE_TIME * 24 * 60 * 60,
            path="/",
            samesite="none" if is_secure else "lax",
            secure=is_secure,
        )
        return {"message": "Login successful", "role": result["role"]}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
def logout(response: Response, request: Request):
    # delete_cookie only works when name, path and the SameSite/Secure pair
    # match how the cookie was set. A bare delete_cookie("token") sends a
    # header without samesite=none/secure, which the browser rejects outright
    # (SameSite=None requires Secure) -- the old cookie survives and the user
    # stays logged in as whoever they were.
    is_secure = _is_secure(request)
    response.delete_cookie(
        key="token",
        path="/",
        httponly=True,
        samesite="none" if is_secure else "lax",
        secure=is_secure,
    )
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        result = auth_service.forgot_password(data.email, db)
        background_tasks.add_task(send_otp_email, result["email"], result["code"], result["purpose"])
        return {"message": result["message"]}
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
    background_tasks: BackgroundTasks,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        result = auth_service.request_change_password_otp(user, db)
        background_tasks.add_task(send_otp_email, result["email"], result["code"], result["purpose"])
        return {"message": result["message"]}
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