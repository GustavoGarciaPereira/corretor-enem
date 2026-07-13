"""Tests for SQLAlchemy models."""

from app.models.models import User, Essay, Competence, Level, CorrectionTemplate


def test_create_user(db_session):
    """Test creating a user."""
    user = User(username="alice", email="alice@test.com", password_hash="hash123")
    db_session.add(user)
    db_session.commit()

    saved = db_session.query(User).filter(User.username == "alice").first()
    assert saved is not None
    assert saved.email == "alice@test.com"
    assert saved.password_hash == "hash123"


def test_create_competence_with_levels(db_session):
    """Test creating a competence with 6 levels."""
    comp = Competence(name="Teste", description="Descrição", max_score=200)
    db_session.add(comp)
    db_session.flush()

    for i in range(6):
        level = Level(
            competence_id=comp.id,
            level_index=i,
            score=i * 40,
            description=f"Nível {i}",
        )
        db_session.add(level)
    db_session.commit()

    # Reload with eager-loaded levels
    comp_db = db_session.query(Competence).filter(Competence.id == comp.id).first()
    assert len(comp_db.levels) == 6
    assert comp_db.levels[0].score == 0
    assert comp_db.levels[5].score == 200


def test_essay_relationships(db_session, test_user, test_template):
    """Test creating an essay linked to user and template."""
    essay = Essay(
        user_id=test_user.id,
        template_id=test_template.id,
        source_type="pasted",
        raw_text="Texto de exemplo.",
        status="pending_correction",
    )
    db_session.add(essay)
    db_session.commit()

    saved = db_session.query(Essay).filter(Essay.id == essay.id).first()
    assert saved.user_id == test_user.id
    assert saved.template_id == test_template.id
    assert saved.user.username == "testuser"


def test_correction_template_with_competences(db_session, test_competences):
    """Test template-competence many-to-many relationship."""
    from app.models.models import TemplateCompetence

    template = CorrectionTemplate(name="Meu Template", description="Teste")
    db_session.add(template)
    db_session.flush()

    for comp in test_competences[:2]:
        db_session.add(TemplateCompetence(template_id=template.id, competence_id=comp.id))
    db_session.commit()
    db_session.refresh(template)

    assert len(template.competences) == 2
    assert template.competences[0].name.startswith("Competência")
