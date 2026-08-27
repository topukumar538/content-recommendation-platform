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

from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    scheduler = None if settings.TESTING else start_scheduler()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)

app = FastAPI(title="ContentPlatform API", version="1.0.0", lifespan=lifespan)


from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    FastAPI returns 422 detail as a list of error dicts. The frontend renders
    detail directly, so a list becomes "[object Object]". Flatten to a string
    so every client gets the same shape for every error response.
    """
    messages = []
    for err in exc.errors():
        loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
        field = loc[-1] if loc else "input"
        messages.append(f"{field}: {err['msg']}")
    return JSONResponse(status_code=422, content={"detail": "; ".join(messages)})

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
                return FileResponse(FRONTEND_DIR / "admin.html")
            else:
                return FileResponse(FRONTEND_DIR / "feed.html")
        except JWTError:
            pass
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/app", StaticFiles(directory=FRONTEND_DIR), name="frontend")