"""Populate default ENEM competences, levels, and template on first run."""

from app.core.database import SessionLocal
from app.models.models import Competence, Level, CorrectionTemplate, TemplateCompetence


DEFAULT_COMPETENCES = [
    {
        "name": "Competência 1",
        "description": "Domínio da modalidade padrão (gramática, ortografia, acentuação, concordância)",
        "max_score": 200,
        "levels": [
            (0, 0, "Desconhecimento total da norma padrão; erros graves e frequentes"),
            (1, 40, "Muitos desvios gramaticais e ortográficos que comprometem a compreensão"),
            (2, 80, "Erros frequentes, mas o texto ainda é compreensível"),
            (3, 120, "Domínio razoável da norma com alguns desvios pontuais"),
            (4, 160, "Bom domínio da norma; poucos erros e de natureza leve"),
            (5, 200, "Excelente domínio da norma padrão, sem erros ou com desvios insignificantes"),
        ],
    },
    {
        "name": "Competência 2",
        "description": "Compreensão do tema e desenvolvimento",
        "max_score": 200,
        "levels": [
            (0, 0, "Não atende ao tipo dissertativo-argumentativo"),
            (1, 40, "Atende ao tipo dissertativo-argumentativo"),
            (2, 80, "Corresponde ao tema proposto, mencionando-o ao menos duas vezes"),
            (3, 120, "Apresenta repertório sociocultural"),
            (4, 160, "Apresenta repertório sociocultural que tem a ver com o tema"),
            (5, 200, "Apresenta repertório que sustenta o argumento defendido"),
        ],
    },
    {
        "name": "Competência 3",
        "description": "Repertório sociocultural (citações, dados, referências)",
        "max_score": 200,
        "levels": [
            (0, 0, "Não apresenta repertório sociocultural"),
            (1, 40, "Repertório desconectado ou mal utilizado"),
            (2, 80, "Repertório citado, mas sem articulação com a tese"),
            (3, 120, "Repertório pertinente e articulado ao tema"),
            (4, 160, "Repertório bem articulado que fortalece a argumentação"),
            (5, 200, "Repertório diversificado, original e plenamente integrado à tese"),
        ],
    },
    {
        "name": "Competência 4",
        "description": "Coesão textual (conectivos, progressão, articulação)",
        "max_score": 200,
        "levels": [
            (0, 0, "Ausência total de recursos coesivos; texto fragmentado"),
            (1, 40, "Uso precário de conectivos; parágrafos desconectados"),
            (2, 80, "Alguns conectivos, mas com falhas de progressão textual"),
            (3, 120, "Boa articulação entre parágrafos e uso adequado de conectivos"),
            (4, 160, "Progressão textual clara com variedade de conectivos"),
            (5, 200, "Excelente coesão; recursos variados e progressão fluida"),
        ],
    },
    {
        "name": "Competência 5",
        "description": "Proposta de intervenção (agente, ação, modo, efeito, respeito aos DH)",
        "max_score": 200,
        "levels": [
            (0, 0, "Ausência de proposta de intervenção"),
            (1, 40, "Proposta vaga ou desconectada do tema"),
            (2, 80, "Proposta presente, mas sem detalhamento dos elementos"),
            (3, 120, "Proposta com agente, ação e modo, mas sem efeito"),
            (4, 160, "Proposta completa com agente, ação, modo e efeito"),
            (5, 200, "Proposta completa e detalhada, respeitando os direitos humanos"),
        ],
    },
]


def seed_default_data():
    """Insert default competences + levels + ENEM template if they don't exist yet."""
    db = SessionLocal()
    try:
        existing = db.query(Competence).filter(Competence.is_default == True).first()
        if existing:
            return  # Already seeded

        comp_objs = []
        for data in DEFAULT_COMPETENCES:
            level_data = data.pop("levels")
            comp = Competence(**data, is_default=True, created_by=None)
            db.add(comp)
            db.flush()

            # Create levels for this competence
            for level_index, score, description in level_data:
                level = Level(
                    competence_id=comp.id,
                    level_index=level_index,
                    score=score,
                    description=description,
                    is_default=True,
                    created_by=None,
                )
                db.add(level)

            comp_objs.append(comp)

        db.flush()

        # Create default template
        template = CorrectionTemplate(
            name="ENEM Oficial",
            description="Template padrão do ENEM com 5 competências e 6 níveis cada",
            is_default=True,
            created_by=None,
        )
        db.add(template)
        db.flush()

        for comp in comp_objs:
            db.add(TemplateCompetence(template_id=template.id, competence_id=comp.id))

        db.commit()
    finally:
        db.close()
