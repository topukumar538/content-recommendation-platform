from pydantic import BaseModel, EmailStr

class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    code: str
    purpose: str

class ResendOTPRequest(BaseModel):
    email: EmailStr
    purpose: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str
    confirm_password: str

class ChangePasswordRequest(BaseModel):
    code: str
    new_password: str
    confirm_password: str