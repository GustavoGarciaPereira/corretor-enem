import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.routers import auth, upload_router, correction_router, page_router, competence_router, template_router  # routers

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
    """Create tables. If it fails (e.g. stale readonly DB), clean up and retry."""
    try:
        Base.metadata.create_all(bind=engine)
        logging.getLogger("app").info("Database tables ready.")
    except Exception as exc:
        logging.warning("create_all failed (%s); cleaning up stale DB files.", exc)
        import glob
        db_path = settings.DATABASE_URL.replace("sqlite:///", "", 1)
        for f in glob.glob(f"{db_path}*"):
            try:
                Path(f).unlink()
            except OSError:
                pass
        Base.metadata.create_all(bind=engine)
        logging.getLogger("app").info("Database tables ready after cleanup.")

    # Seed default competences / template
    from app.core.seed import seed_default_data
    seed_default_data()
    logging.getLogger("app").info("Default data seeded.")


# ─── Routers ─────────────────────────────────────────────────────────────────

app.include_router(auth.router, prefix="", tags=["auth"])
app.include_router(upload_router.router, prefix="", tags=["upload"])
app.include_router(correction_router.router, prefix="", tags=["correction"])
app.include_router(page_router.router, prefix="", tags=["pages"])
app.include_router(competence_router.router, prefix="", tags=["admin"])
app.include_router(template_router.router, prefix="", tags=["admin"])


# ─── Health check ────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}
