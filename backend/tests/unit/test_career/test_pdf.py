from __future__ import annotations

from typing import Any


def _payload() -> dict[str, Any]:
    return {
        "contract_version": "career_report_read_v1",
        "report_id": "report-1",
        "generation_id": "generation-1",
        "status": "narrative_failed",
        "version": 1,
        "versions": {},
        "deterministic_payload": {
            "top_dimensions": [
                {
                    "fact_key": "dimension:systems_thinking",
                    "dimension": "systems_thinking",
                    "score": 88,
                    "confidence": 0.84,
                }
            ],
            "contradictions": [
                {
                    "fact_key": "contradiction:leadership_without_people_management",
                    "code": "leadership_without_people_management",
                    "capability_score": 82,
                }
            ],
            "context_constraints": ["experience:senior", "constraints:provided"],
            "role_matches": [
                {
                    "fact_key": "role:architecture",
                    "role_family_key": "architecture",
                    "category": "strong_match",
                    "profession_examples": ["Solution Architect"],
                    "reasons": ["dimension:systems_thinking"],
                }
            ],
        },
        "sections": [
            {
                "section_key": "professional_summary",
                "title": "Ваш профессиональный профиль",
                "body": "Системное мышление помогает связывать ограничения и решения.",
            }
        ],
        "section_states": [
            {"section_key": "professional_summary", "status": "ready", "error": None},
            {"section_key": "work_style", "status": "failed", "error": "career_provider_failure"},
        ],
        "assembled_payload": {},
    }


def test_career_pdf_uses_progressive_reader_payload_and_keeps_deterministic_content() -> None:
    from app.modules.career.pdf import generate_career_report_pdf, render_career_report_html

    payload = _payload()
    html = render_career_report_html(report_payload=payload, profile_name="Алина")

    assert "Алина" in html
    assert "Ваш профессиональный профиль" in html
    assert "Системное мышление" in html
    assert "88" in html
    assert "не является оценкой" in html
    assert "Solution Architect" in html
    assert "возможный пример" in html.lower()
    assert "Часть пояснений временно недоступна" in html
    assert "experience:senior" not in html
    assert "Опыт: уверенный профессиональный уровень" in html

    pdf = generate_career_report_pdf(report_payload=payload, profile_name="Алина")
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
