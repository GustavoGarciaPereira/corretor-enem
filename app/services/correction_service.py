import json
from datetime import datetime

import httpx

from app.core.config import settings
from app.core.database import SessionLocal, run_sync
from app.models.models import Essay, Correction

# ─── System Prompts ──────────────────────────────────────────────────────────

SYSTEM_PROMPT_A = (
    "Você é um corretor RIGOROSO da redação do ENEM. "
    "Seu foco principal é avaliar com dureza a Competência 1 (domínio da norma culta: gramática, ortografia, concordância) "
    "e a Competência 4 (coesão: uso de conectivos, progressão textual, articulação entre parágrafos). "
    "Cada competência vale de 0 a 200 pontos. Seja crítico e detalhista."
)

SYSTEM_PROMPT_B = (
    "Você é um corretor PROGRESSISTA da redação do ENEM. "
    "Seu foco principal é valorizar a Competência 2 (compreensão do tema e desenvolvimento), "
    "a Competência 3 (repertório sociocultural: citações, dados, referências) "
    "e a Competência 5 (intervenção: proposta detalhada e respeitosa aos direitos humanos). "
    "Cada competência vale de 0 a 200 pontos. Seja generoso quando o texto mostrar boas ideias."
)

SYSTEM_PROMPT_C = (
    "Você é um corretor EQUILIBRADO da redação do ENEM. "
    "Analise todas as 5 competências com justiça e imparcialidade. "
    "Cada competência vale de 0 a 200 pontos. Seu voto é o desempate."
)

USER_PROMPT_TEMPLATE = (
    'Corrija a redação ENEM abaixo. '
    'Notas de 0 a 200 por competência. '
    'Retorne APENAS JSON válido, sem markdown, sem explicações extras, no formato: '
    '{{"c1":{{"nota":int,"justificativa":"..."}},'
    '"c2":{{"nota":int,"justificativa":"..."}},'
    '"c3":{{"nota":int,"justificativa":"..."}},'
    '"c4":{{"nota":int,"justificativa":"..."}},'
    '"c5":{{"nota":int,"justificativa":"..."}},'
    '"total":int}}\n\n'
    'REDAÇÃO:\n{text}'
)

CORRECTOR_CONFIG = {
    "A": {"system_prompt": SYSTEM_PROMPT_A, "temperature": 0.3},
    "B": {"system_prompt": SYSTEM_PROMPT_B, "temperature": 0.8},
    "C": {"system_prompt": SYSTEM_PROMPT_C, "temperature": 0.5},
}


async def call_deepseek_corrector(essay_text: str, corrector_type: str) -> dict:
    """Call the DeepSeek API for one correction pass and return parsed JSON."""
    cfg = CORRECTOR_CONFIG[corrector_type]

    if not settings.DEEPSEEK_API_KEY or settings.DEEPSEEK_API_KEY.startswith("sk-placeholder"):
        return _mock_correction(corrector_type)

    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": cfg["system_prompt"]},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=essay_text)},
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


def _mock_correction(corrector_type: str) -> dict:
    """Return simulated correction for development without an API key."""
    import random
    base = 100 if corrector_type == "A" else 120
    c = {
        "c1": base + random.randint(-20, 20),
        "c2": base + random.randint(-20, 20),
        "c3": base + random.randint(-20, 20),
        "c4": base + random.randint(-20, 20),
        "c5": base + random.randint(-20, 20),
    }
    c["total"] = c["c1"] + c["c2"] + c["c3"] + c["c4"] + c["c5"]
    return {
        corrector_type: {
            "c1": {"nota": c["c1"], "justificativa": "[Mock] Avaliação simulada."},
            "c2": {"nota": c["c2"], "justificativa": "[Mock] Avaliação simulada."},
            "c3": {"nota": c["c3"], "justificativa": "[Mock] Avaliação simulada."},
            "c4": {"nota": c["c4"], "justificativa": "[Mock] Avaliação simulada."},
            "c5": {"nota": c["c5"], "justificativa": "[Mock] Avaliação simulada."},
            "total": c["total"],
        }
    }


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
        raise ValueError(f"Failed to parse JSON from {corrector_type} response: {content[:200]}")

    return {corrector_type: result}


async def perform_double_correction(essay_id: int, essay_text: str):
    """Run dual correction (A + B), save results, decide if C is needed."""
    import asyncio

    # Step 1: Run A and B in parallel
    results = await asyncio.gather(
        call_deepseek_corrector(essay_text, "A"),
        call_deepseek_corrector(essay_text, "B"),
    )

    corrections_data = {}
    for r in results:
        corrections_data.update(r)

    # Step 2: Save A and B to DB
    db = SessionLocal()
    try:
        for ct in ("A", "B"):
            data = corrections_data[ct]
            _save_correction(db, essay_id, ct, data)
            db.commit()

        # Step 3: Check score difference
        score_a = corrections_data["A"]["total"]
        score_b = corrections_data["B"]["total"]
        diff = abs(score_a - score_b)

        final_corrections = {"A": corrections_data["A"], "B": corrections_data["B"]}

        if diff > 100:
            # Step 4: Call tiebreaker C
            c_result = await call_deepseek_corrector(essay_text, "C")
            corrections_data.update(c_result)
            _save_correction(db, essay_id, "C", c_result["C"])
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


def _save_correction(db, essay_id: int, corrector_type: str, data: dict):
    """Insert a Correction row from parsed API data."""
    correction = Correction(
        essay_id=essay_id,
        corrector_type=corrector_type,
        total_score=data.get("total"),
        c1=data.get("c1", {}).get("nota") if isinstance(data.get("c1"), dict) else data.get("c1"),
        c2=data.get("c2", {}).get("nota") if isinstance(data.get("c2"), dict) else data.get("c2"),
        c3=data.get("c3", {}).get("nota") if isinstance(data.get("c3"), dict) else data.get("c3"),
        c4=data.get("c4", {}).get("nota") if isinstance(data.get("c4"), dict) else data.get("c4"),
        c5=data.get("c5", {}).get("nota") if isinstance(data.get("c5"), dict) else data.get("c5"),
        feedback_json=json.dumps(data, ensure_ascii=False),
    )
    db.add(correction)
