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

    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: NarrativeInput,
        schema: type[StructuredSchemaT],
    ) -> StructuredSchemaT:
        del prompt
        del narrative_input

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
