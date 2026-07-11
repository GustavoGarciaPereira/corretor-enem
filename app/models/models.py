from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    essays = relationship("Essay", back_populates="user", cascade="all, delete-orphan")


class Essay(Base):
    __tablename__ = "essays"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=True)
    source_type = Column(String(20), nullable=False, default="pasted")  # pasted | scanned
    raw_text = Column(Text, nullable=True)
    status = Column(
        String(30),
        nullable=False,
        default="pending_correction",  # pending_review | pending_correction | completed | failed
    )
    final_score = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="essays")
    corrections = relationship("Correction", back_populates="essay", cascade="all, delete-orphan")


class Correction(Base):
    __tablename__ = "corrections"

    id = Column(Integer, primary_key=True, index=True)
    essay_id = Column(Integer, ForeignKey("essays.id"), nullable=False)
    corrector_type = Column(String(1), nullable=False)  # 'A', 'B', or 'C'
    total_score = Column(Integer, nullable=True)
    c1 = Column(Integer, nullable=True)
    c2 = Column(Integer, nullable=True)
    c3 = Column(Integer, nullable=True)
    c4 = Column(Integer, nullable=True)
    c5 = Column(Integer, nullable=True)
    feedback_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    essay = relationship("Essay", back_populates="corrections")
