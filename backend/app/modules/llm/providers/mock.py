# ruff: noqa: RUF001
"""Deterministic mock provider for local development and tests."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from app.modules.astrotype_v2.schemas import ReportSegmentOutputV2, SectionRenderInputV2
from app.modules.report_narratives.schemas import NarrativeInput

StructuredSchemaT = TypeVar("StructuredSchemaT", bound=BaseModel)


def _v2_mock_payload(section: SectionRenderInputV2) -> dict[str, object]:
    """Render only supplied owned themes; this is labelled demo prose, not LLM quality evidence."""
    moves = {
        "psychological_mechanism": (
            "Внутренний механизм рассматривается здесь как способ связывать переживание с выбором действия. "
            "В демонстрационном режиме мы не добавляем новых выводов о человеке: используем только переданное "
            "описание этой темы и сохраняем его ограниченный смысл, без обещания универсальной точности."
        ),
        "lived_manifestation": (
            "В повседневной жизни описание можно сопоставить с конкретной ситуацией, а не принимать за неизменное "
            "правило поведения. Полезно различать само наблюдение и его объяснение: одинаковый внешний поступок "
            "может иметь разные причины, поэтому контекст остаётся необходимым условием аккуратного прочтения."
        ),
        "inner_tension": (
            "Внутреннее напряжение не означает обязательный конфликт или недостаток личности. Речь идёт о "
            "возможной полярности между привычным способом реагировать и другим доступным выбором. Тестовый "
            "текст сохраняет эту неопределённость и не превращает описание темы в диагноз или прогноз событий."
        ),
        "protective_strategy": (
            "Защитная стратегия рассматривается без обвинения: под давлением человек может выбирать более "
            "привычную реакцию, потому что она понятнее в данный момент. Для проверки смысла важно замечать "
            "условия появления реакции и отличать полезную защиту от автоматического повторения знакомого сценария."
        ),
        "immature_expression": (
            "Автоматическое выражение темы имеет смысл обсуждать через наблюдаемое действие, а не через оценку "
            "человека целиком. В этом демонстрационном описании нет требования немедленно менять себя: сначала "
            "можно определить ситуацию, заметить собственный ответ и проверить, "
            "действительно ли предложенное объяснение подходит."
        ),
        "mature_expression": (
            "Зрелое выражение предполагает возможность выбирать ответ с учётом ситуации и собственных ограничений. "
            "Это не обещание идеального поведения и не сравнение с другими людьми. Переданная тема служит "
            "точкой для наблюдения, а решение о её применимости остаётся за самим читателем."
        ),
        "integration_question": (
            "Для самопроверки полезно вернуться к конкретному эпизоду и отделить факты от привычной интерпретации. "
            "Можно заметить, что помогло сохранить свободу выбора, а что усилило напряжение. Вопрос ниже относится "
            "только к переданной теме; дополнительные биографические детали "
            "или неподтверждённые объяснения не добавляются."
        ),
    }
    paragraphs = [
        "Демонстрационный текст локального mock-провайдера. Это проверка структуры отчёта, не результат реальной LLM."
    ]
    for field, explanation in moves.items():
        values = [
            value.replace(theme.title, "эта тема") for theme in section.owned_themes if (value := getattr(theme, field))
        ]
        paragraphs.append(explanation + " " + " ".join(values))
    paragraphs.extend(
        [
            (
                "Для тестовой проверки важно отделять устройство отчёта от его содержательной точности. "
                "Этот демонстрационный вариант показывает, как сохраняются границы раздела, последовательность "
                "абзацев и связь с переданными основаниями. Он не подтверждает, что какое-либо описание относится "
                "к конкретному читателю, и не заменяет внимательного сопоставления с личным опытом. Если исходная "
                "тема содержит только краткое описание, отсутствующие подробности не восстанавливаются по догадке. "
                "Нельзя автоматически заключать, что человеку свойственны определённые поступки, переживания "
                "или отношения. Вопрос о применимости остаётся открытым: для содержательной интерпретации нужны "
                "отдельные наблюдения и полноценный разбор, которых структурный тест сам по себе не предоставляет."
            ),
            (
                "При чтении демонстрации полезно также различать возможность и обязательность. Упоминание "
                "напряжения, защиты или зрелого ответа здесь обозначает часть формата, а не установленное "
                "свойство личности. Это не свидетельство произошедшего события и не предсказание будущего. "
                "Смысл проверки состоит в том, чтобы показать связный порядок изложения без добавления чужих "
                "тем, неподтверждённых деталей и категоричных оценок. Даже знакомая формулировка не должна "
                "становиться основанием для важных решений о себе или другом человеке. Сначала следует "
                "проверить исходные данные, затем понять ограниченность предложенного описания и только после "
                "этого обсуждать его возможную связь с конкретной ситуацией в соответствующем контексте."
            ),
            (
                "Отдельная граница этой демонстрации касается результата технической проверки. Корректное "
                "отображение текста означает лишь, что приложение умеет принять подготовленный ответ, сохранить "
                "его структуру и показать читателю согласованные разделы. Оно ничего не доказывает о качестве "
                "работы реального языкового сервиса, стоимости его вызовов или точности психологических выводов. "
                "Демонстрационный ответ не обращается к внешнему провайдеру и не получает дополнительные сведения "
                "о биографии. Поэтому его уместно использовать для проверки навигации, чтения и сохранения "
                "отчёта, но не как готовое персональное заключение. Эта оговорка сохраняется независимо от "
                "объёма исходной темы и количества переданных оснований для раздела."
            ),
        ]
    )
    return {
        "contract_version": "report_segment_output_v2",
        "section_id": section.section_id,
        "title": section.section_title,
        "body": "\n\n".join(paragraphs),
        "covered_theme_ids": [theme.id for theme in section.owned_themes],
        "evidence_ids": list(section.evidence_ids),
        "continuation_complete": True,
        "continuation_cursor": None,
        "notes": ["native mock; no network; not real-provider quality evidence"],
    }


class MockLLMProvider:
    """Return a stable, schema-valid narrative without any network calls."""

    model_name = "mock-self-v1"
    supports_staged_pipeline = True

    def __init__(self, *, allow_v2_mock: bool = True) -> None:
        self._allow_v2_mock = allow_v2_mock

    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: NarrativeInput | SectionRenderInputV2,
        schema: type[StructuredSchemaT],
    ) -> StructuredSchemaT:
        del prompt

        if isinstance(narrative_input, SectionRenderInputV2):
            if not self._allow_v2_mock:
                raise ValueError("Native Self v2 mock is unavailable in production")
            if schema is not ReportSegmentOutputV2:
                raise TypeError("Self v2 mock requires its segment output contract")
            return schema.model_validate(_v2_mock_payload(narrative_input))

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
