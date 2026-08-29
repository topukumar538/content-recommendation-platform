from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from jose import JWTError

from database import Base, engine, SessionLocal
from models import User
from routes import auth, feed, admin, user
from core.security import decode_token
from core.config import settings
from scheduler import start_scheduler
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
    """
    Landing redirect.

    Role is re-read from the database rather than taken from the JWT payload.
    The token carries the role it had at login and lives for 7 days, so a
    promotion or demotion would otherwise not reach this route until the user
    logged out and back in -- while every other route, which depends on
    get_current_active_user, would already reflect the change. That split is
    confusing to debug: the API says admin, the landing page says user.

    A blocked user is sent to the landing page rather than a feed they would
    be denied on the next request anyway.
    """
    token = request.cookies.get("token")
    if token:
        try:
            payload = decode_token(token)
        except JWTError:
            return FileResponse(FRONTEND_DIR / "index.html")

        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.id == payload.get("user_id")).first()
            if db_user and not db_user.is_blocked:
                page = "admin.html" if db_user.role == "admin" else "feed.html"
                return FileResponse(FRONTEND_DIR / page)
        finally:
            db.close()

    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/app", StaticFiles(directory=FRONTEND_DIR), name="frontend")