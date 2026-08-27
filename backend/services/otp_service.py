import secrets
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from models import OTPCode
from core.config import settings

import logging

logger = logging.getLogger(__name__)

DEMO_OTP_CODE = "123456"


def generate_otp() -> str:
    if settings.DEMO_MODE:
        return DEMO_OTP_CODE
    return ''.join(secrets.choice(string.digits) for _ in range(6))


def send_otp_email(email: str, code: str, purpose: str):
    if settings.DEMO_MODE:
        # No SMTP egress on the demo host; the frontend surfaces the fixed code.
        print(f"[DEMO_MODE] OTP for {email} ({purpose}): {code} — email not sent")
        return

    subject = "Your OTP Code — ContentPlatform"
    if purpose == "signup":
        body = f"""Welcome to ContentPlatform!

Your verification code is: {code}

This code expires in {settings.OTP_EXPIRE_MIN} minutes.
Do not share this code with anyone."""
    elif purpose == "forgot_password":
        body = f"""ContentPlatform — Password Reset

Your verification code is: {code}

This code expires in {settings.OTP_EXPIRE_MIN} minutes.
If you did not request this, ignore this email."""
    else:
        body = f"""ContentPlatform — Password Change

Your verification code is: {code}

This code expires in {settings.OTP_EXPIRE_MIN} minutes.
If you did not request this, ignore this email."""

    msg = MIMEMultipart()
    msg["From"] = settings.GMAIL_USER
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.GMAIL_USER, settings.GMAIL_PASSWORD)
            server.sendmail(settings.GMAIL_USER, email, msg.as_string())
    except Exception:
        logger.exception("OTP delivery failed for %s (purpose=%s)", email, purpose)
        raise


def create_otp(email: str, purpose: str, db: Session) -> str:
    # delete old OTPs
    db.query(OTPCode).filter(
        OTPCode.email == email,
        OTPCode.purpose == purpose,
        OTPCode.is_used == False
    ).delete()
    db.commit()

    # generate and save new OTP
    code = generate_otp()
    otp = OTPCode(email=email, code=code, purpose=purpose)
    db.add(otp)
    db.commit()

    return code   # delivery is handled by the caller via BackgroundTasks


MAX_OTP_ATTEMPTS = 5


def verify_otp(email: str, code: str, purpose: str, db: Session) -> bool:
    otp = db.query(OTPCode).filter(
        OTPCode.email == email,
        OTPCode.purpose == purpose,
        OTPCode.is_used == False
    ).first()

    if not otp:
        raise ValueError("Invalid OTP. Please request a new one.")

    # check expiry
    # created_at is DateTime(timezone=True), but SQLite (tests) returns naive
    # values. Assume UTC when naive rather than stripping the offset, which
    # would shift expiry by the server's UTC offset.
    created_at = otp.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    expiry = created_at + timedelta(minutes=settings.OTP_EXPIRE_MIN)
    if datetime.now(timezone.utc) > expiry:
        raise ValueError("OTP expired. Please request a new one.")

    # check if locked
    if otp.attempts >= MAX_OTP_ATTEMPTS:
        raise ValueError("Too many wrong attempts. Please request a new OTP.")

    # wrong code — increment attempts
    if otp.code != code:
        otp.attempts += 1
        remaining = MAX_OTP_ATTEMPTS - otp.attempts
        db.commit()
        if remaining == 0:
            raise ValueError("Too many wrong attempts. Please request a new OTP.")
        raise ValueError(f"Wrong OTP. {remaining} attempts remaining.")

    # correct code
    otp.is_used = True
    db.commit()
    return True