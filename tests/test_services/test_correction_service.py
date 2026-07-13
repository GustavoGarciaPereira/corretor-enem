"""Tests for correction_service.py."""

import json
from unittest.mock import patch, MagicMock

from app.services.correction_service import (
    build_user_prompt,
    _parse_json_response,
    _mock_level_correction,
)


def test_build_user_prompt(test_competences):
    """Test building the prompt with level options."""
    competences = test_competences[:1]
    prompt = build_user_prompt("Texto de teste", competences)

    assert "Competência 1" in prompt
    assert "Nível 0" in prompt
    assert "Nível 5" in prompt
    assert "Texto de teste" in prompt
    assert "JSON" in prompt


def test_parse_json_response():
    """Test parsing a clean JSON response from the AI."""
    response = json.dumps({
        "comp_1": {"level": 3, "justificativa": "Bom domínio"},
        "comp_2": {"level": 4, "justificativa": "Ótimo tema"},
        "total": 700,
    })
    # Create mock competences with level data
    competences = _make_mock_competences(2)
    result = _parse_json_response(response, "A", competences)
    assert result["A"]["comp_1"]["level"] == 3
    assert result["A"]["comp_1"]["score"] == 120  # level 3 * 40
    assert result["A"]["comp_2"]["level"] == 4
    assert result["A"]["total"] == 280  # (3*40) + (4*40)


def test_parse_json_response_with_markdown():
    """Test parsing a response wrapped in ```json ```."""
    response = """```json
{"comp_1": {"level": 3, "justificativa": "Bom"}, "total": 600}
```"""
    competences = _make_mock_competences(1)
    result = _parse_json_response(response, "A", competences)
    assert result["A"]["comp_1"]["level"] == 3
    assert result["A"]["total"] == 120


def test_mock_level_correction(test_competences):
    """Test the mock correction picks levels from available ones."""
    competences = test_competences[:2]
    result = _mock_level_correction("A", competences)

    assert "A" in result
    comp1 = result["A"]["comp_1"]
    assert "level" in comp1
    assert "justificativa" in comp1
    # The mock returns level index; score is computed by _parse_json_response
    assert 0 <= comp1["level"] <= 5
    assert result["A"]["total"] >= 0


def _make_mock_competences(count):
    """Helper to create mock competence objects for parsing tests."""
    from app.models.models import Competence, Level

    competences = []
    for i in range(count):
        comp = Competence(
            id=i + 1,
            name=f"Comp {i+1}",
            description=f"Desc {i+1}",
            max_score=200,
        )
        comp.levels = [
            Level(level_index=j, score=j * 40, description=f"Nível {j}")
            for j in range(6)
        ]
        competences.append(comp)
    return competences



