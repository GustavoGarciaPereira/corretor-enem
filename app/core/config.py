import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project root: two levels up from this file (core/config.py -> core/ -> app/ -> project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings:
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "sk-placeholder-change-me")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "sua_chave_super_secreta_32_bytes")
    _db_url: str = os.getenv("DATABASE_URL", "sqlite:///./instance/app.db")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    @property
    def DATABASE_URL(self) -> str:
        """Resolve relative SQLite paths against the project root."""
        url = self._db_url
        if url.startswith("sqlite:///./"):
            relative = url.replace("sqlite:///./", "")
            absolute = str(PROJECT_ROOT / relative)
            return f"sqlite:///{absolute}"
        return url


settings = Settings()
