import json

import httpx

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import Essay, Correction, Competence, CorrectionTemplate, TemplateCompetence

# ─── System Prompts ──────────────────────────────────────────────────────────

SYSTEM_PROMPT_A = (
    "Você é um corretor RIGOROSO de redação. "
    "Seu foco principal é avaliar com dureza a correção gramatical (ortografia, concordância, regência) "
    "e a coesão textual (conectivos, progressão, articulação entre parágrafos). "
    "Seja crítico e detalhista nas justificativas."
)

SYSTEM_PROMPT_B = (
    "Você é um corretor PROGRESSISTA de redação. "
    "Seu foco principal é valorizar a compreensão do tema, o repertório sociocultural "
    "e a proposta de intervenção. "
    "Seja generoso quando o texto mostrar boas ideias e criatividade."
)

SYSTEM_PROMPT_C = (
    "Você é um corretor EQUILIBRADO de redação. "
    "Analise todas as competências com justiça e imparcialidade. "
    "Seu voto é o desempate."
)

CORRECTOR_CONFIG = {
    "A": {"system_prompt": SYSTEM_PROMPT_A, "temperature": 0.3},
    "B": {"system_prompt": SYSTEM_PROMPT_B, "temperature": 0.8},
    "C": {"system_prompt": SYSTEM_PROMPT_C, "temperature": 0.5},
}


# ─── Dynamic prompt builder ──────────────────────────────────────────────────

def build_user_prompt(text: str, competences: list[Competence]) -> str:
    """Build a prompt listing all competences dynamically."""
    comp_list = "\n".join(
        f"{i+1}. {c.name}: {c.description} (0 a {c.max_score})"
        for i, c in enumerate(competences)
    )
    return (
        "Corrija a redação abaixo de acordo com as seguintes competências:\n\n"
        f"{comp_list}\n\n"
        "Para cada competência, retorne um objeto JSON com 'nota' (int) e 'justificativa' (string).\n"
        "Retorne APENAS JSON válido, sem markdown, no formato:\n"
        '{"comp_1": {"nota": int, "justificativa": "..."},'
        ' "comp_2": {...}, ..., "total": int}\n\n'
        f"Redação:\n{text}"
    )


# ─── Get competences for a template ──────────────────────────────────────────

def get_competences_for_template(template_id: int) -> list[Competence]:
    """Fetch all competences associated with a given template."""
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
    """Return the id of the default ENEM template (creates if missing)."""
    db = SessionLocal()
    try:
        template = (
            db.query(CorrectionTemplate)
            .filter(CorrectionTemplate.is_default == True)
            .first()
        )
        if template:
            return template.id
        # If no default template exists yet, try to seed
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


# ─── API call ────────────────────────────────────────────────────────────────

async def call_deepseek_corrector(
    essay_text: str, corrector_type: str, competences: list[Competence]
) -> dict:
    """Call the DeepSeek API for one correction pass with dynamic competences."""
    cfg = CORRECTOR_CONFIG[corrector_type]

    if not settings.DEEPSEEK_API_KEY or settings.DEEPSEEK_API_KEY.startswith("sk-placeholder"):
        return _mock_dynamic_correction(corrector_type, competences)

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

    return _parse_json_response(content, corrector_type)


def _mock_dynamic_correction(corrector_type: str, competences: list[Competence]) -> dict:
    """Return simulated correction for development without an API key."""
    import random

    result = {}
    total = 0
    for i, comp in enumerate(competences, start=1):
        nota = random.randint(comp.max_score // 2, comp.max_score)
        key = f"comp_{i}"
        result[key] = {
            "nota": nota,
            "justificativa": f"[Mock {corrector_type}] Avaliação simulada para '{comp.name}'.",
        }
        total += nota
    result["total"] = total
    return {corrector_type: result}


def _parse_json_response(content: str, corrector_type: str) -> dict:
    """Parse the LLM response into a structured dict, stripping markdown fences."""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        raise ValueError(
            f"Failed to parse JSON from {corrector_type} response: {content[:200]}"
        )

    return {corrector_type: result}


# ─── Orchestration ───────────────────────────────────────────────────────────

async def perform_double_correction(essay_id: int, essay_text: str):
    """Run dual correction (A + B), save results, decide if C is needed."""
    import asyncio

    # Fetch competences for this essay's template
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
            # Fallback: create a single generic competence
            competences = [
                Competence(name="Avaliação Geral", description="Nota geral da redação", max_score=1000)
            ]
    finally:
        db.close()

    # Step 1: Run A and B in parallel
    results = await asyncio.gather(
        call_deepseek_corrector(essay_text, "A", competences),
        call_deepseek_corrector(essay_text, "B", competences),
    )

    corrections_data = {}
    for r in results:
        corrections_data.update(r)

    # Step 2: Save A and B to DB
    db = SessionLocal()
    try:
        for ct in ("A", "B"):
            data = corrections_data[ct]
            _save_correction(db, essay_id, ct, data, competences)
            db.commit()

        # Step 3: Check score difference
        score_a = corrections_data["A"]["total"]
        score_b = corrections_data["B"]["total"]
        diff = abs(score_a - score_b)

        if diff > 100:
            # Step 4: Call tiebreaker C
            c_result = await call_deepseek_corrector(essay_text, "C", competences)
            corrections_data.update(c_result)
            _save_correction(db, essay_id, "C", c_result["C"], competences)
            db.commit()

            # Step 5: Find the two closest scores and average them
            score_c = c_result["C"]["total"]
            pairs = [
                (abs(score_a - score_b), ("A", "B")),
                (abs(score_a - score_c), ("A", "C")),
                (abs(score_b - score_c), ("B", "C")),
            ]
            pairs.sort(key=lambda x: x[0])
            best_pair_keys = pairs[0][1]

            final_scores = {
                k: corrections_data[k]["total"] for k in best_pair_keys
            }
            final_score = sum(final_scores.values()) // len(final_scores)
        else:
            final_score = (score_a + score_b) // 2

        # Step 6: Update essay status
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
    """Insert a Correction row, storing both scores_json and backward-compat c1..c5."""
    # Build scores_json with competence names
    scores_json = {}
    total = data.get("total", 0)
    for i, comp in enumerate(competences, start=1):
        key = f"comp_{i}"
        comp_data = data.get(key, {})
        scores_json[key] = {
            "nome": comp.name,
            "nota": comp_data.get("nota", 0) if isinstance(comp_data, dict) else comp_data,
            "max_score": comp.max_score,
            "justificativa": comp_data.get("justificativa", "") if isinstance(comp_data, dict) else "",
        }
    scores_json["total"] = total

    # Also fill c1..c5 for backward compatibility (map comp_1→c1, etc.)
    c_vals = {}
    for i in range(1, 6):
        key = f"comp_{i}"
        comp_data = data.get(key, {})
        c_vals[f"c{i}"] = comp_data.get("nota", None) if isinstance(comp_data, dict) else None

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
