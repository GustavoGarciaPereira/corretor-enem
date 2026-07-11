from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
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
    competences = relationship(
        "Competence", back_populates="creator", cascade="all, delete-orphan"
    )
    templates = relationship(
        "CorrectionTemplate", back_populates="creator", cascade="all, delete-orphan"
    )


# ─── Competence / Template / Level ───────────────────────────────────────────


class Level(Base):
    __tablename__ = "levels"

    id = Column(Integer, primary_key=True, index=True)
    competence_id = Column(Integer, ForeignKey("competences.id"), nullable=False)
    level_index = Column(Integer, nullable=False)  # 0, 1, 2, 3, 4, 5
    score = Column(Integer, nullable=False)        # 0, 40, 80, 120, 160, 200
    description = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    competence = relationship("Competence", back_populates="levels")


class Competence(Base):
    __tablename__ = "competences"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    max_score = Column(Integer, nullable=False, default=200)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    creator = relationship("User", back_populates="competences")
    levels = relationship(
        "Level", back_populates="competence", cascade="all, delete-orphan",
        order_by="Level.level_index", lazy="selectin",
    )


class CorrectionTemplate(Base):
    __tablename__ = "correction_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    creator = relationship("User", back_populates="templates")
    competences = relationship(
        "Competence", secondary="template_competences", lazy="selectin"
    )


class TemplateCompetence(Base):
    __tablename__ = "template_competences"

    template_id = Column(
        Integer, ForeignKey("correction_templates.id"), primary_key=True
    )
    competence_id = Column(
        Integer, ForeignKey("competences.id"), primary_key=True
    )


# ─── Essay ───────────────────────────────────────────────────────────────────


class Essay(Base):
    __tablename__ = "essays"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    template_id = Column(
        Integer, ForeignKey("correction_templates.id"), nullable=True
    )
    filename = Column(String(255), nullable=True)
    source_type = Column(String(20), nullable=False, default="pasted")
    raw_text = Column(Text, nullable=True)
    status = Column(
        String(30),
        nullable=False,
        default="pending_correction",
    )
    final_score = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="essays")
    template = relationship("CorrectionTemplate")
    corrections = relationship(
        "Correction", back_populates="essay", cascade="all, delete-orphan"
    )


# ─── Correction ──────────────────────────────────────────────────────────────


class Correction(Base):
    __tablename__ = "corrections"

    id = Column(Integer, primary_key=True, index=True)
    essay_id = Column(Integer, ForeignKey("essays.id"), nullable=False)
    corrector_type = Column(String(1), nullable=False)
    total_score = Column(Integer, nullable=True)
    c1 = Column(Integer, nullable=True)
    c2 = Column(Integer, nullable=True)
    c3 = Column(Integer, nullable=True)
    c4 = Column(Integer, nullable=True)
    c5 = Column(Integer, nullable=True)
    feedback_json = Column(Text, nullable=True)
    scores_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    essay = relationship("Essay", back_populates="corrections")
