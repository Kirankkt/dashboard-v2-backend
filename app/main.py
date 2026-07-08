from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models  # noqa: F401  (register models on Base)
from .config import get_settings
from .database import SessionLocal, get_db
from .db_migrate import run_migrations
from .models import User
from .routers import auth, projects, tasks
from .security import decode_token

settings = get_settings()

if settings.jwt_secret in ("dev-secret-change-me", "change-me-to-a-long-random-string"):
    print("WARNING: JWT_SECRET is a placeholder — set a strong secret in the environment.")

run_migrations()

if settings.seed_on_start:
    from .seed import seed

    seed()

app = FastAPI(title="Dashboard v2 API")


@app.middleware("http")
async def attach_user(request: Request, call_next):
    """Attach the logged-in user + role to every request (if a valid token
    is present). Enforcement is left to route dependencies."""
    request.state.user = None
    request.state.role = None

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        payload = decode_token(auth_header[7:])
        if payload and payload.get("sub"):
            try:
                user_id = int(payload["sub"])
            except (TypeError, ValueError):
                user_id = None
            if user_id is not None:
                db = SessionLocal()
                try:
                    user = db.get(User, user_id)
                    if user is not None:
                        db.expunge(user)
                        request.state.user = user
                        request.state.role = user.role
                finally:
                    db.close()

    return await call_next(request)


_origins = (
    ["*"]
    if settings.cors_origins.strip() == "*"
    else [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok", "db": "up" if db_ok else "down"}
