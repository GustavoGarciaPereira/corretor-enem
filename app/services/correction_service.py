import json

import httpx

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import (
    Essay,
    Correction,
    Competence,
    Level,
    CorrectionTemplate,
    TemplateCompetence,
)

# ─── System Prompts ──────────────────────────────────────────────────────────

SYSTEM_PROMPT_A = (
    "Você é um corretor RIGOROSO de redação. "
    "Seu foco é avaliar com dureza a correção gramatical e a coesão textual. "
    "Seja crítico e detalhista nas justificativas."
)

SYSTEM_PROMPT_B = (
    "Você é um corretor PROGRESSISTA de redação. "
    "Seu foco é valorizar compreensão do tema, repertório e proposta de intervenção. "
    "Seja generoso quando o texto mostrar boas ideias."
)

SYSTEM_PROMPT_C = (
    "Você é um corretor EQUILIBRADO de redação. "
    "Analise todas as competências com justiça e imparcialidade. Seu voto é o desempate."
)

CORRECTOR_CONFIG = {
    "A": {"system_prompt": SYSTEM_PROMPT_A, "temperature": 0.3},
    "B": {"system_prompt": SYSTEM_PROMPT_B, "temperature": 0.8},
    "C": {"system_prompt": SYSTEM_PROMPT_C, "temperature": 0.5},
}


# ─── Dynamic prompt builder ──────────────────────────────────────────────────

def build_user_prompt(text: str, competences: list[Competence]) -> str:
    """Build a prompt listing competences with their level options."""
    sections = []
    for i, comp in enumerate(competences, start=1):
        lines = [f"Competência {i}: {comp.name} – {comp.description} (0 a {comp.max_score})"]
        sorted_levels = sorted(comp.levels or [], key=lambda x: x.level_index)
        for lvl in sorted_levels:
            lines.append(f"  Nível {lvl.level_index} ({lvl.score} pts): {lvl.description}")
        sections.append("\n".join(lines))

    comp_block = "\n\n".join(sections)

    return (
        "Corrija a redação abaixo de acordo com as seguintes competências.\n"
        "Para cada competência, escolha o nível que melhor descreve o texto.\n\n"
        f"{comp_block}\n\n"
        "Retorne APENAS JSON válido, sem markdown, no formato:\n"
        '{"comp_1": {"level": int, "justificativa": "..."},'
        ' "comp_2": {"level": int, "justificativa": "..."}, ..., "total": int}\n\n'
        f"Redação:\n{text}"
    )


# ─── Get competences for a template ──────────────────────────────────────────

def get_competences_for_template(template_id: int) -> list[Competence]:
    db = SessionLocal()
    try:
        competences = (
            db.query(Competence)
            .join(TemplateCompetence)
            .filter(TemplateCompetence.template_id == template_id)
            .all()
        )
        return list(competences)
    finally:
        db.close()


def get_or_create_default_template() -> int:
    db = SessionLocal()
    try:
        template = (
            db.query(CorrectionTemplate)
            .filter(CorrectionTemplate.is_default == True)
            .first()
        )
        if template:
            return template.id
        from app.core.seed import seed_default_data
        seed_default_data()
        template = (
            db.query(CorrectionTemplate)
            .filter(CorrectionTemplate.is_default == True)
            .first()
        )
        return template.id if template else 0
    finally:
        db.close()


def _get_level_for_competence(competence_id: int, level_index: int) -> Level | None:
    """Fetch a specific level by competence_id and level_index."""
    db = SessionLocal()
    try:
        return (
            db.query(Level)
            .filter(
                Level.competence_id == competence_id,
                Level.level_index == level_index,
            )
            .first()
        )
    finally:
        db.close()


# ─── API call ────────────────────────────────────────────────────────────────

async def call_deepseek_corrector(
    essay_text: str, corrector_type: str, competences: list[Competence]
) -> dict:
    """Call the DeepSeek API for one correction pass with level-based scoring."""
    cfg = CORRECTOR_CONFIG[corrector_type]

    if not settings.DEEPSEEK_API_KEY or settings.DEEPSEEK_API_KEY.startswith("sk-placeholder"):
        return _mock_level_correction(corrector_type, competences)

    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    user_prompt = build_user_prompt(essay_text, competences)

    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": cfg["system_prompt"]},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": cfg["temperature"],
        "max_tokens": 4096,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.deepseek.com/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]

    return _parse_json_response(content, corrector_type, competences)


def _mock_level_correction(corrector_type: str, competences: list[Competence]) -> dict:
    """Return simulated level-based correction."""
    import random

    result = {}
    total = 0
    for i, comp in enumerate(competences, start=1):
        sorted_levels = sorted(comp.levels or [], key=lambda x: x.level_index)
        if sorted_levels:
            chosen = random.choice(sorted_levels)
            level_idx = chosen.level_index
            score = chosen.score
            desc = chosen.description
        else:
            level_idx = random.randint(0, 5)
            score = level_idx * 40
            desc = f"Nível {level_idx}"

        key = f"comp_{i}"
        result[key] = {
            "level": level_idx,
            "justificativa": f"[Mock {corrector_type}] Nível {level_idx} escolhido para '{comp.name}': {desc}",
        }
        total += score
    result["total"] = total
    return {corrector_type: result}


def _parse_json_response(
    content: str, corrector_type: str, competences: list[Competence]
) -> dict:
    """Parse the LLM response. Expects {'comp_1': {'level': int, ...}, 'total': int}."""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        raise ValueError(
            f"Failed to parse JSON from {corrector_type} response: {content[:200]}"
        )

    # Build competence_id → Level map for this set of competences
    comp_id_map = {}
    for comp in competences:
        for lvl in (comp.levels or []):
            comp_id_map[(comp.id, lvl.level_index)] = lvl

    result = {}
    total = 0
    for i, comp in enumerate(competences, start=1):
        key = f"comp_{i}"
        raw = parsed.get(key, {})
        level_idx = raw.get("level", 0) if isinstance(raw, dict) else 0
        justificativa = raw.get("justificativa", "") if isinstance(raw, dict) else ""

        # Look up the level details
        found_level = comp_id_map.get((comp.id, level_idx))
        if found_level:
            score = found_level.score
            description = found_level.description
        else:
            score = level_idx * 40
            description = f"Nível {level_idx}"

        result[key] = {
            "level": level_idx,
            "score": score,
            "description": description,
            "justificativa": justificativa,
        }
        total += score

    result["total"] = total
    return {corrector_type: result}


# ─── Orchestration ───────────────────────────────────────────────────────────

async def perform_double_correction(essay_id: int, essay_text: str):
    """Run dual correction (A + B), save results, decide if C is needed."""
    import asyncio

    db = SessionLocal()
    try:
        essay = db.query(Essay).filter(Essay.id == essay_id).first()
        if not essay:
            return {"final_score": 0}

        template_id = essay.template_id
        if not template_id:
            template_id = get_or_create_default_template()

        competences = get_competences_for_template(template_id)
        if not competences:
            competences = [
                Competence(
                    name="Avaliação Geral",
                    description="Nota geral da redação",
                    max_score=1000,
                )
            ]
    finally:
        db.close()

    results = await asyncio.gather(
        call_deepseek_corrector(essay_text, "A", competences),
        call_deepseek_corrector(essay_text, "B", competences),
    )

    corrections_data = {}
    for r in results:
        corrections_data.update(r)

    db = SessionLocal()
    try:
        for ct in ("A", "B"):
            data = corrections_data[ct]
            _save_correction(db, essay_id, ct, data, competences)
            db.commit()

        score_a = corrections_data["A"]["total"]
        score_b = corrections_data["B"]["total"]
        diff = abs(score_a - score_b)

        if diff > 100:
            c_result = await call_deepseek_corrector(essay_text, "C", competences)
            corrections_data.update(c_result)
            _save_correction(db, essay_id, "C", c_result["C"], competences)
            db.commit()

            score_c = c_result["C"]["total"]
            pairs = [
                (abs(score_a - score_b), ("A", "B")),
                (abs(score_a - score_c), ("A", "C")),
                (abs(score_b - score_c), ("B", "C")),
            ]
            pairs.sort(key=lambda x: x[0])
            best_pair_keys = pairs[0][1]
            final_scores = {k: corrections_data[k]["total"] for k in best_pair_keys}
            final_score = sum(final_scores.values()) // len(final_scores)
        else:
            final_score = (score_a + score_b) // 2

        essay = db.query(Essay).filter(Essay.id == essay_id).first()
        if essay:
            essay.status = "completed"
            essay.final_score = final_score
            db.commit()
    finally:
        db.close()

    return {"final_score": final_score}


# ─── Save helper ─────────────────────────────────────────────────────────────

def _save_correction(
    db,
    essay_id: int,
    corrector_type: str,
    data: dict,
    competences: list[Competence],
):
    """Insert a Correction row with scores_json in the new level-based format."""
    scores_json = {}
    total = data.get("total", 0)

    for i, comp in enumerate(competences, start=1):
        key = f"comp_{i}"
        comp_data = data.get(key, {})
        if isinstance(comp_data, dict):
            scores_json[key] = {
                "nome": comp.name,
                "level": comp_data.get("level", 0),
                "score": comp_data.get("score", 0),
                "description": comp_data.get("description", ""),
                "max_score": comp.max_score,
                "justificativa": comp_data.get("justificativa", ""),
            }
        else:
            scores_json[key] = {
                "nome": comp.name,
                "level": 0,
                "score": 0,
                "description": "",
                "max_score": comp.max_score,
                "justificativa": "",
            }

    scores_json["total"] = total

    # Fill c1..c5 for backward compat
    c_vals = {}
    for i in range(1, 6):
        key = f"comp_{i}"
        cd = data.get(key, {}) if isinstance(data.get(key), dict) else {}
        c_vals[f"c{i}"] = cd.get("score", None)

    correction = Correction(
        essay_id=essay_id,
        corrector_type=corrector_type,
        total_score=total,
        c1=c_vals["c1"],
        c2=c_vals["c2"],
        c3=c_vals["c3"],
        c4=c_vals["c4"],
        c5=c_vals["c5"],
        feedback_json=json.dumps(data, ensure_ascii=False),
        scores_json=scores_json,
    )
    db.add(correction)
