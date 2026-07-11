from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.routers import auth, upload_router  # routers

# ─── App instance ────────────────────────────────────────────────────────────

app = FastAPI(title="Correção de Redação", version="0.1.0")

# ─── Middleware ──────────────────────────────────────────────────────────────

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# ─── Static files ────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# ─── Create tables on startup ───────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


# ─── Routers ─────────────────────────────────────────────────────────────────

app.include_router(auth.router, prefix="", tags=["auth"])
app.include_router(upload_router.router, prefix="", tags=["upload"])


# ─── Health check ────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}
