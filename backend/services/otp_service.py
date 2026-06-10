import secrets
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import OTPCode
from core.config import settings

def generate_otp() -> str:
    return ''.join(secrets.choice(string.digits) for _ in range(6))

def send_otp_email(email: str, code: str, purpose: str):
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
    except Exception as e:
        print(f"Email sending failed: {e}")
        raise Exception("Failed to send OTP email")

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

    return code   # ← just returns code, no email sent here anymore


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
    created_at = otp.created_at.replace(tzinfo=None)
    expiry = created_at + timedelta(minutes=settings.OTP_EXPIRE_MIN)
    if datetime.utcnow() > expiry:
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