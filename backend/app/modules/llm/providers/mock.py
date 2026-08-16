# ruff: noqa: RUF001
"""Deterministic mock provider for local development and tests."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from app.modules.report_narratives.schemas import NarrativeInput

StructuredSchemaT = TypeVar("StructuredSchemaT", bound=BaseModel)


class MockLLMProvider:
    """Return a stable, schema-valid narrative without any network calls."""

    model_name = "mock-self-v1"
    supports_staged_pipeline = True

    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: NarrativeInput,
        schema: type[StructuredSchemaT],
    ) -> StructuredSchemaT:
        del prompt

        schema_name = schema.__name__
        synthesis = narrative_input.deep_natal_synthesis
        evidence_ids = list(synthesis.evidence_map.keys())[:3] if synthesis is not None else ["moon_trine_mercury"]
        if schema_name == "NarrativePlan":
            return schema.model_validate(
                {
                    "prompt_version": "self_plan_v2",
                    "sections": [
                        {
                            "section_id": "identity",
                            "title": "Как собирается ваша идентичность",
                            "required_evidence_ids": evidence_ids,
                            "focus": "Главная формула и сильные стороны.",
                        },
                        {
                            "section_id": "emotional",
                            "title": "Как вы переживаете и выражаете напряжение",
                            "required_evidence_ids": evidence_ids,
                            "focus": "Эмоции, речь и уязвимости.",
                        },
                        {
                            "section_id": "relationships",
                            "title": "Как вы строите близость",
                            "required_evidence_ids": evidence_ids,
                            "focus": "Отношения и доверие.",
                        },
                        {
                            "section_id": "development",
                            "title": "Вектор развития",
                            "required_evidence_ids": evidence_ids,
                            "focus": "Рост и зрелая интеграция напряжений.",
                        },
                        {
                            "section_id": "house_scenarios",
                            "title": "Жизненные сценарии",
                            "required_evidence_ids": evidence_ids,
                            "focus": "Дома и практическое проявление карты.",
                        },
                    ],
                    "global_guardrails": ["Только evidence-backed claims"],
                    "assembly_notes": "Собери единый narrative-first Self report без соционики.",
                }
            )
        if schema_name == "IdentitySectionOutput":
            return schema.model_validate(
                {
                    "section_id": "identity",
                    "title": "Как собирается ваша идентичность",
                    "paragraphs": [
                        (
                            "Вы строите идентичность через сочетание внутренней собранности "
                            "и внимательности к смыслу происходящего."
                        ),
                        "В сильной форме это даёт способность держать личную линию и не терять нюансы ситуации.",
                    ],
                    "evidence_ids": evidence_ids,
                    "covered_pattern_ids": ["identity_pattern"],
                }
            )
        if schema_name == "EmotionalSectionOutput":
            return schema.model_validate(
                {
                    "section_id": "emotional",
                    "title": "Как вы переживаете и выражаете напряжение",
                    "paragraphs": [
                        (
                            "Эмоции быстро связываются с мыслью, поэтому переживание почти сразу "
                            "требует языка, объяснения и формы."
                        ),
                        (
                            "Уязвимость появляется там, где хочется немедленно назвать и проконтролировать "
                            "то, что ещё созревает внутри."
                        ),
                    ],
                    "evidence_ids": evidence_ids,
                    "covered_pattern_ids": ["emotional_pattern"],
                }
            )
        if schema_name == "RelationshipSectionOutput":
            return schema.model_validate(
                {
                    "section_id": "relationships",
                    "title": "Как вы строите близость",
                    "paragraphs": [
                        (
                            "В отношениях вам важна не формальная близость, а ощущение живого контакта "
                            "и эмоциональной достоверности."
                        ),
                        (
                            "Доверие растёт там, где другой человек выдерживает глубину "
                            "и не обесценивает ваши тонкие реакции."
                        ),
                    ],
                    "evidence_ids": evidence_ids,
                    "covered_pattern_ids": ["relationship_pattern"],
                }
            )
        if schema_name == "DevelopmentSectionOutput":
            return schema.model_validate(
                {
                    "section_id": "development",
                    "title": "Вектор развития",
                    "paragraphs": [
                        (
                            "Рост начинается там, где вы не пытаетесь мгновенно исправить "
                            "внутреннее напряжение, а выдерживаете паузу."
                        ),
                        "Зрелая форма — превращать чувствительность в наблюдение, выбор и ясное действие.",
                    ],
                    "evidence_ids": evidence_ids,
                    "covered_pattern_ids": ["development_pattern"],
                }
            )
        if schema_name == "HouseScenariosSectionOutput":
            return schema.model_validate(
                {
                    "section_id": "house_scenarios",
                    "title": "Жизненные сценарии",
                    "paragraphs": [
                        "Ключевые сферы жизни включаются через поиск смысла, глубины и внутренней честности.",
                        "Практический ресурс появляется, когда карта становится не диагнозом, а языком выбора.",
                    ],
                    "evidence_ids": evidence_ids,
                    "covered_pattern_ids": ["house_pattern"],
                }
            )
        if schema_name == "AssemblyCheck":
            return schema.model_validate(
                {
                    "duplicate_claim_ids": [],
                    "missing_required_evidence_ids": [],
                    "tone_notes": ["Собранный текст держит плотный Self-first тон."],
                    "needs_retry": False,
                }
            )

        payload = {
            "title": "Ваш внутренний портрет",
            "hero": {
                "id": "hero",
                "title": "Главное о вас",
                "body": (
                    "Вы производите впечатление человека, который соединяет "
                    "эмоциональную глубину и выразительное мышление."
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
            "dominants": [
                {
                    "id": "dominant_fire",
                    "title": "Доминирующая стихия: Огонь",
                    "body": "Огонь задаёт способ быстро включаться через инициативу и выразительность.",
                    "evidence_ids": ["mercury_venus_jupiter_leo_8"],
                }
            ],
            "inner_mechanism": {
                "title": "Внутренний механизм личности",
                "summary": "Паттерн разворачивается от импульса к выражению и затем к осмыслению реакции среды.",
                "steps": [
                    {
                        "id": "mechanism_notice",
                        "title": "Сначала вы считываете эмоциональный фон",
                        "body": "Вы быстро замечаете настроение и скрытый смысл ситуации.",
                        "evidence_ids": ["moon_trine_mercury"],
                    },
                    {
                        "id": "mechanism_express",
                        "title": "Затем формулируете образно и заразительно",
                        "body": "Смысл становится заметным через речь, интонацию и образ.",
                        "evidence_ids": ["mercury_venus_jupiter_leo_8"],
                    },
                    {
                        "id": "mechanism_integrate",
                        "title": "После этого ищете форму для переживания",
                        "body": (
                            "Внутреннее напряжение легче выдерживать, когда оно названо и собрано в понятную историю."
                        ),
                        "evidence_ids": ["moon_trine_mercury"],
                    },
                ],
            },
            "house_scenarios": [item.model_dump(mode="json") for item in narrative_input.house_scenarios]
            or [
                {
                    "id": "house_scenario_mock",
                    "title": "Сценарий дома",
                    "placement": "Солнце в 9 доме",
                    "need": "Иметь собственную систему смысла.",
                    "manifestation": "Вы ищете объяснение, которое собирает опыт в понятную картину.",
                    "shadow": "Можно откладывать действие ради идеальной системы.",
                    "mature_expression": "Зрелая форма — применять знание в выборе.",
                    "evidence_ids": ["mercury_venus_jupiter_leo_8"],
                    "evidence_notes": [],
                }
            ],
            "calibration_questions": [item.model_dump(mode="json") for item in narrative_input.calibration_questions],
            "contradictions": [item.model_dump(mode="json") for item in narrative_input.contradictions],
            "failure_modes": [item.model_dump(mode="json") for item in narrative_input.failure_modes],
            "maturity_levels": narrative_input.maturity_levels.model_dump(mode="json"),
            "sections": [
                {
                    "id": "main_formula",
                    "title": "Главная формула личности",
                    "body": "Вы раскрываетесь через сильное эмоциональное присутствие и образное мышление.",
                    "bullets": [
                        "Видите подтекст.",
                        "Умеете влиять через интонацию и формулировку.",
                    ],
                    "evidence_notes": [
                        {
                            "claim": "Выразительное мышление связано с эмоциональной интенсивностью.",
                            "fact_ids": ["mercury_venus_jupiter_leo_8", "moon_trine_mercury"],
                        }
                    ],
                }
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
        return schema.model_validate(payload)
