"""Populate default ENEM competences and template on first run."""

from app.core.database import SessionLocal
from app.models.models import Competence, CorrectionTemplate, TemplateCompetence


DEFAULT_COMPETENCES = [
    {
        "name": "Competência 1",
        "description": "Domínio da modalidade padrão (gramática, ortografia, acentuação, concordância)",
        "max_score": 200,
    },
    {
        "name": "Competência 2",
        "description": "Compreensão do tema e desenvolvimento",
        "max_score": 200,
    },
    {
        "name": "Competência 3",
        "description": "Repertório sociocultural (citações, dados, referências)",
        "max_score": 200,
    },
    {
        "name": "Competência 4",
        "description": "Coesão textual (conectivos, progressão, articulação)",
        "max_score": 200,
    },
    {
        "name": "Competência 5",
        "description": "Proposta de intervenção (agente, ação, modo, efeito, respeito aos DH)",
        "max_score": 200,
    },
]


def seed_default_data():
    """Insert default competences + ENEM template if they don't exist yet."""
    db = SessionLocal()
    try:
        existing = db.query(Competence).filter(Competence.is_default == True).first()
        if existing:
            return  # Already seeded

        # Create competences
        comp_objs = []
        for data in DEFAULT_COMPETENCES:
            comp = Competence(**data, is_default=True, created_by=None)
            db.add(comp)
            comp_objs.append(comp)
        db.flush()

        # Create default template
        template = CorrectionTemplate(
            name="ENEM Oficial",
            description="Template padrão do ENEM com 5 competências",
            is_default=True,
            created_by=None,
        )
        db.add(template)
        db.flush()

        # Associate competences with template
        for comp in comp_objs:
            db.add(TemplateCompetence(template_id=template.id, competence_id=comp.id))

        db.commit()
    finally:
        db.close()
