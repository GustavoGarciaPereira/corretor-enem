from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


# ─── User ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Essay ───────────────────────────────────────────────────────────────────

class EssayCreate(BaseModel):
    raw_text: str
    source_type: str = "pasted"  # pasted | scanned
    filename: Optional[str] = None


class EssayOut(BaseModel):
    id: int
    user_id: int
    filename: Optional[str]
    source_type: str
    raw_text: Optional[str]
    status: str
    final_score: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Correction ──────────────────────────────────────────────────────────────

class CorrectionOut(BaseModel):
    id: int
    essay_id: int
    corrector_type: str  # 'A', 'B', or 'C'
    total_score: Optional[int]
    c1: Optional[int]
    c2: Optional[int]
    c3: Optional[int]
    c4: Optional[int]
    c5: Optional[int]
    feedback_json: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
