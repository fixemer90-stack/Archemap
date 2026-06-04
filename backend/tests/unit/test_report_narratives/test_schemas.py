# ruff: noqa: RUF001
"""Unit tests for report narrative schemas."""

from __future__ import annotations

from pydantic import ValidationError

from app.modules.report_narratives.schemas import NarrativeInput, SelfNarrative


def make_narrative_input_payload() -> dict[str, object]:
    """Create a valid NarrativeInput payload for tests."""
    return {
        "product": "self",
        "language": "ru",
        "profile": {
            "name": "Алексей",
            "birth_date": "1991-08-29",
            "birth_time_quality": "exact",
            "birth_place": "Москва",
        },
        "calculation_quality": {
            "has_exact_birth_time": True,
            "has_known_birth_time": True,
            "quality_label": "Высокая точность времени рождения",
            "warning": None,
        },
        "key_facts": [
            {
                "id": "mercury_venus_jupiter_leo_8",
                "label": "Меркурий, Венера и Юпитер во Льве в 8 доме",
                "meaning": "Выразительное мышление и эмоциональное влияние.",
            }
        ],
        "key_aspects": [
            {
                "id": "moon_trine_mercury",
                "label": "Луна тригон Меркурий",
                "orb": "0°50′",
                "meaning": "Связь эмоций и речи.",
            }
        ],
        "socionics": {
            "type": "EIE",
            "type_ru": "ЭИЭ",
            "confidence_label": "средняя",
            "explanation": "Этико-интуитивная выразительность.",
        },
        "archetype": {
            "primary": "Наставник",
            "confidence_label": "высокая",
            "explanation": "Склонность собирать людей вокруг смысла.",
        },
        "strengths": [
            {
                "id": "strength_expression",
                "claim": "Вы умеете заражать идеей.",
                "evidence_ids": ["mercury_venus_jupiter_leo_8", "moon_trine_mercury"],
            }
        ],
        "risks": [
            {
                "id": "risk_overload",
                "claim": "Иногда эмоции перегружают речь.",
                "evidence_ids": ["moon_trine_mercury"],
            }
        ],
        "relationship_patterns": [
            {
                "id": "relationships_depth",
                "claim": "Вам важна эмоциональная интенсивность и глубина доверия.",
                "evidence_ids": ["mercury_venus_jupiter_leo_8"],
            }
        ],
        "sexuality_patterns": [
            {
                "id": "sexuality_intensity",
                "claim": "Близость раскрывается через доверие и внутреннюю вовлечённость.",
                "evidence_ids": ["mercury_venus_jupiter_leo_8"],
            }
        ],
        "development_recommendations": [
            {
                "id": "development_grounding",
                "claim": "Полезно давать себе паузу перед эмоционально важным разговором.",
                "evidence_ids": ["moon_trine_mercury"],
            }
        ],
        "product_boundaries": {
            "career_policy": "В Self-отчёте карьеру затрагивать кратко и завершать CTA на Career.",
            "allowed_sections": [
                "main_formula",
                "world_perception",
                "emotions_and_communication",
                "strengths",
                "vulnerabilities",
                "relationships",
                "sexuality",
                "development",
            ],
        },
    }


def make_self_narrative_payload() -> dict[str, object]:
    """Create a valid SelfNarrative payload for tests."""
    return {
        "title": "Ваш внутренний портрет",
        "hero": {
            "id": "hero",
            "title": "Главное о вас",
            "body": (
                "Вы производите впечатление человека, который соединяет эмоциональную глубину и выразительное мышление."
            ),
            "bullets": [
                "Умеете передавать настроение через слова.",
                "Чувствуете скрытый эмоциональный фон ситуации.",
            ],
            "evidence_notes": [
                {
                    "claim": "Эмоции и речь работают в связке.",
                    "fact_ids": ["moon_trine_mercury"],
                }
            ],
        },
        "sections": [
            {
                "id": "main_formula",
                "title": "Главная формула личности",
                "body": "Вы раскрываетесь через сильное эмоциональное присутствие и образное мышление.",
                "bullets": ["Видите подтекст.", "Умеете влиять через интонацию и формулировку."],
                "evidence_notes": [
                    {
                        "claim": "Выразительное мышление связано с эмоциональной интенсивностью.",
                        "fact_ids": ["mercury_venus_jupiter_leo_8", "moon_trine_mercury"],
                    }
                ],
            },
            {
                "id": "world_perception",
                "title": "Как вы воспринимаете мир",
                "body": "Вы быстро замечаете настроение, смысл и скрытые мотивы происходящего.",
                "bullets": [],
                "evidence_notes": [],
            },
        ],
        "career_cta": {
            "title": "Отдельный отчёт Career",
            "body": (
                "Если захотите глубже разобрать работу и профессиональную роль, "
                "это лучше вынести в отдельный Career-отчёт."
            ),
            "bullets": ["Профроли", "среда", "стратегия роста"],
            "button_label": "Открыть Career",
        },
        "final_summary": "Ваш сильный эффект рождается там, где чувства, речь и смысл собираются в одно целое.",
    }


class TestNarrativeInputSchema:
    """Validate NarrativeInput contract."""

    def test_accepts_self_payload(self) -> None:
        payload = make_narrative_input_payload()

        result = NarrativeInput.model_validate(payload)

        assert result.product == "self"
        assert result.language == "ru"
        assert result.profile.name == "Алексей"
        assert result.product_boundaries.allowed_sections[0] == "main_formula"
        assert result.strengths[0].evidence_ids == ["mercury_venus_jupiter_leo_8", "moon_trine_mercury"]

    def test_rejects_unsupported_product(self) -> None:
        payload = make_narrative_input_payload()
        payload["product"] = "friendship"

        try:
            NarrativeInput.model_validate(payload)
        except ValidationError as exc:
            assert "product" in str(exc)
        else:
            raise AssertionError("NarrativeInput unexpectedly accepted unsupported product")


class TestSelfNarrativeSchema:
    """Validate SelfNarrative contract."""

    def test_accepts_structured_narrative(self) -> None:
        payload = make_self_narrative_payload()

        result = SelfNarrative.model_validate(payload)

        assert result.title == "Ваш внутренний портрет"
        assert result.hero.id == "hero"
        assert result.sections[0].id == "main_formula"
        assert result.sections[1].id == "world_perception"
        assert result.sections[0].evidence_notes[0].fact_ids == [
            "mercury_venus_jupiter_leo_8",
            "moon_trine_mercury",
        ]

    def test_rejects_unknown_section_id(self) -> None:
        payload = make_self_narrative_payload()
        payload["sections"][0]["id"] = "career_strategy"  # type: ignore[index]

        try:
            SelfNarrative.model_validate(payload)
        except ValidationError as exc:
            assert "sections.0.id" in str(exc) or "section" in str(exc)
        else:
            raise AssertionError("SelfNarrative unexpectedly accepted unknown section id")

    def test_requires_career_cta(self) -> None:
        payload = make_self_narrative_payload()
        payload.pop("career_cta")

        try:
            SelfNarrative.model_validate(payload)
        except ValidationError as exc:
            assert "career_cta" in str(exc)
        else:
            raise AssertionError("SelfNarrative unexpectedly accepted payload without career_cta")
