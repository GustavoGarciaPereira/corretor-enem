import asyncio
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Ensure the parent directory of the SQLite database exists
_db_url_path = settings.DATABASE_URL.replace("sqlite:///", "", 1)
_db_path = Path(_db_url_path)
_db_path.parent.mkdir(parents=True, exist_ok=True)

# ─── Stale-file cleanup ──────────────────────────────────────────────────────
# Crashed processes can leave WAL/SHM files that make SQLite appear read-only.
_db_str = str(_db_path)
for stale_ext in ("-wal", "-shm", "-journal"):
    stale = Path(_db_str + stale_ext)
    if stale.exists():
        try:
            stale.unlink()
        except OSError:
            pass

# ─── Engine ──────────────────────────────────────────────────────────────────

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={
        "check_same_thread": False,
        "timeout": 15,  # SQLite busy timeout in seconds
    },
)


@event.listens_for(engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
    """Set safe SQLite PRAGMAs on every new connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=DELETE")       # No WAL (avoids stale -wal/-shm)
    cursor.execute("PRAGMA busy_timeout=15000")         # 15s busy timeout
    cursor.execute("PRAGMA synchronous=NORMAL")          # Balance safety/speed
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def run_sync(fn, *args, **kwargs):
    """Run a synchronous DB function in a thread pool so async code doesn't block."""
    return await asyncio.to_thread(fn, *args, **kwargs)
