from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from database import Base, engine
from routes import auth, feed, admin, user
from core.security import decode_token
from jose import JWTError
from scheduler import start_scheduler
from core.config import settings
from services.otp_service import DEMO_OTP_CODE

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ContentPlatform API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth.router)
app.include_router(feed.router)
app.include_router(admin.router)
app.include_router(user.router)



@app.get("/config")
def get_config():
    return {
        "demo_mode": settings.DEMO_MODE,
        "demo_otp": DEMO_OTP_CODE if settings.DEMO_MODE else None,
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root(request: Request):
    token = request.cookies.get("token")
    if token:
        try:
            payload = decode_token(token)
            role = payload.get("role")
            if role == "admin":
                return FileResponse("../frontend/admin.html")
            else:
                return FileResponse("../frontend/feed.html")
        except JWTError:
            pass
    return FileResponse("../frontend/index.html")

app.mount("/app", StaticFiles(directory="../frontend"), name="frontend")