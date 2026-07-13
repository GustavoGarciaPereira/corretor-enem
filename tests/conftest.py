"""Shared fixtures for all tests (sync SQLAlchemy)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models.models import (
    User,
    Essay,
    Competence,
    Level,
    CorrectionTemplate,
    TemplateCompetence,
)

TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Override FastAPI dependency to use test DB (ensures tables exist)."""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """Ensure tables exist before each test, clean up after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """Return a test DB session."""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """Return a FastAPI TestClient."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def test_user(db_session):
    """Create and return a test user."""
    import bcrypt

    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode("utf-8"),
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def auth_client(client, test_user):
    """Return a client already logged in as test_user."""
    client.post("/login", data={"username": "testuser", "password": "password123"})
    return client


@pytest.fixture
def test_competences(db_session):
    """Create 5 default competences with 6 levels each."""
    competences = []
    for i in range(1, 6):
        comp = Competence(
            name=f"Competência {i}",
            description=f"Descrição da competência {i}",
            max_score=200,
            is_default=True,
            created_by=None,
        )
        db_session.add(comp)
        competences.append(comp)
    db_session.flush()

    for comp in competences:
        for level_idx in range(6):
            level = Level(
                competence_id=comp.id,
                level_index=level_idx,
                score=level_idx * 40,
                description=f"Nível {level_idx} - {comp.name}",
                is_default=True,
            )
            db_session.add(level)
    db_session.commit()
    return competences


@pytest.fixture
def test_template(db_session, test_competences):
    """Create a template associated with all default competences."""
    template = CorrectionTemplate(
        name="Template Teste",
        description="Template para testes",
        is_default=True,
        created_by=None,
    )
    db_session.add(template)
    db_session.flush()

    for comp in test_competences:
        db_session.add(
            TemplateCompetence(template_id=template.id, competence_id=comp.id)
        )
    db_session.commit()
    db_session.refresh(template)
    return template


@pytest.fixture
def test_essay(db_session, test_user, test_template):
    """Create an essay pending correction."""
    essay = Essay(
        user_id=test_user.id,
        template_id=test_template.id,
        source_type="pasted",
        raw_text="Texto da redação de teste para correção ENEM.",
        status="pending_correction",
    )
    db_session.add(essay)
    db_session.commit()
    db_session.refresh(essay)
    return essay
