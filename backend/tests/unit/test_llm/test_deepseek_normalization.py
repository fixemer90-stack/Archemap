import json

from app.modules.llm.providers.deepseek import DeepSeekProvider
from app.modules.report_narratives.schemas import (
    EmotionalSectionOutput,
    IdentitySectionOutput,
    NarrativePlan,
    RelationshipSectionOutput,
)


def _provider() -> DeepSeekProvider:
    return DeepSeekProvider(api_key="test", model="deepseek-v4-flash", timeout_seconds=180, max_retries=2)


def test_parse_response_normalizes_legacy_narrative_plan_shape() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "narrative_plan": {
                                "contract_version": "deep_natal_synthesis_v1",
                                "stage_order": [
                                    "main_formula",
                                    "world_perception",
                                    "emotions_and_communication",
                                    "strengths",
                                    "vulnerabilities",
                                    "relationships",
                                    "sexuality",
                                    "development",
                                    "house_scenarios",
                                ],
                                "sections": {
                                    "main_formula": {
                                        "title": "Основная формула личности",
                                        "evidence_ids": ["fact_a", "fact_b"],
                                        "description": "Главный личностный паттерн.",
                                    },
                                    "world_perception": {
                                        "title": "Восприятие мира",
                                        "evidence_ids": ["fact_c"],
                                        "description": "Как человек видит мир.",
                                    },
                                    "relationships": {
                                        "title": "Отношения",
                                        "evidence_ids": ["fact_d"],
                                        "description": "Динамика близости.",
                                    },
                                    "development": {
                                        "title": "Развитие",
                                        "evidence_ids": ["fact_e"],
                                        "description": "Точка роста.",
                                    },
                                    "house_scenarios": {
                                        "title": "Жизненные сценарии по домам",
                                        "evidence_ids": ["fact_f"],
                                        "description": "Как дома формируют сюжет.",
                                    },
                                },
                            }
                        },
                        ensure_ascii=False,
                    )
                }
            }
        ]
    }

    result = _provider()._parse_response(payload, NarrativePlan)

    assert result.prompt_version == "self_plan_v1"
    assert [section.section_id for section in result.sections] == [
        "identity",
        "emotional",
        "relationships",
        "development",
        "house_scenarios",
    ]
    assert result.sections[0].required_evidence_ids == ["fact_a", "fact_b", "fact_c"]
    assert result.sections[0].focus
    assert result.global_guardrails
    assert result.assembly_notes


def test_parse_response_normalizes_flat_legacy_identity_section_shape() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "identity": "Первый абзац про идентичность.",
                            "worldview": "Второй абзац про мировосприятие.",
                            "position": "Третий абзац про позицию в жизни.",
                            "evidence_ids": ["fact_a", "fact_b"],
                        },
                        ensure_ascii=False,
                    )
                }
            }
        ]
    }

    result = _provider()._parse_response(payload, IdentitySectionOutput)

    assert result.section_id == "identity"
    assert result.title == "Идентичность и опора личности"
    assert result.paragraphs == [
        "Первый абзац про идентичность.",
        "Второй абзац про мировосприятие.",
        "Третий абзац про позицию в жизни.",
    ]
    assert result.evidence_ids == ["fact_a", "fact_b"]
    assert result.covered_pattern_ids == ["fact_a", "fact_b"]


def test_parse_response_normalizes_wrapped_identity_section_shape() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "identity_section": {
                                "title": "Как собрана идентичность",
                                "summary": "Сводка по идентичности.",
                                "worldview": "Как человек видит мир.",
                                "position": "Как он занимает позицию.",
                            }
                        },
                        ensure_ascii=False,
                    )
                }
            }
        ]
    }

    result = _provider()._parse_response(payload, IdentitySectionOutput)

    assert result.section_id == "identity"
    assert result.title == "Как собрана идентичность"
    assert result.paragraphs == [
        "Сводка по идентичности.",
        "Как человек видит мир.",
        "Как он занимает позицию.",
    ]
    assert result.evidence_ids == ["fallback_evidence"]
    assert result.covered_pattern_ids == ["fallback_evidence"]


def test_parse_response_normalizes_identity_summary_shape() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "identity_summary": "Сводка идентичности.",
                            "worldview": "Мировосприятие.",
                            "position": "Позиция в мире.",
                            "evidence_ids": ["fact_a", "fact_b"],
                        },
                        ensure_ascii=False,
                    )
                }
            }
        ]
    }

    result = _provider()._parse_response(payload, IdentitySectionOutput)

    assert result.section_id == "identity"
    assert result.paragraphs == [
        "Сводка идентичности.",
        "Мировосприятие.",
        "Позиция в мире.",
    ]
    assert result.evidence_ids == ["fact_a", "fact_b"]
    assert result.covered_pattern_ids == ["fact_a", "fact_b"]


def test_parse_response_normalizes_live_emotional_section_shape() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "emotional_processing": "Как запускается эмоциональный процесс.",
                            "emotional_expression": "Как эмоции выражаются вовне.",
                            "emotional_regulation": "Как человек регулирует внутреннее напряжение.",
                            "chart_dynamics": [
                                {
                                    "id": "chart_dynamic_1",
                                    "evidence_ids": ["fact_a"],
                                    "mechanism": "Механизм.",
                                }
                            ],
                            "contradictions": [
                                {
                                    "id": "contradiction_1",
                                    "evidence_ids": ["fact_b"],
                                    "manifestation": "Проявление напряжения.",
                                }
                            ],
                        },
                        ensure_ascii=False,
                    )
                }
            }
        ]
    }

    result = _provider()._parse_response(payload, EmotionalSectionOutput)

    assert result.section_id == "emotional"
    assert result.title == "Эмоциональная динамика"
    assert result.paragraphs == [
        "Как запускается эмоциональный процесс.",
        "Как эмоции выражаются вовне.",
        "Как человек регулирует внутреннее напряжение.",
        "Проявление напряжения.",
    ]
    assert result.evidence_ids == ["fact_a", "fact_b"]
    assert result.covered_pattern_ids == ["chart_dynamic_1", "contradiction_1"]


def test_parse_response_normalizes_wrapped_relationships_section_shape() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "relationships_sexuality": {
                                "title": "Отношения и близость",
                                "content": [
                                    {
                                        "source": "venus_mars_pattern",
                                        "evidence_ids": ["fact_a"],
                                        "psychological_mechanism": "Психологический механизм.",
                                        "life_manifestation": "Жизненное проявление.",
                                        "risk": "Риск автоматизма.",
                                    },
                                    {
                                        "source": "contradiction_1",
                                        "evidence_ids": ["fact_b"],
                                        "mechanism": "Второй механизм.",
                                        "manifestation": "Второе проявление.",
                                        "mature_expression": "Зрелая форма.",
                                    },
                                ],
                            }
                        },
                        ensure_ascii=False,
                    )
                }
            }
        ]
    }

    result = _provider()._parse_response(payload, RelationshipSectionOutput)

    assert result.section_id == "relationships"
    assert result.title == "Отношения и близость"
    assert result.evidence_ids == ["fact_a", "fact_b"]
    assert result.covered_pattern_ids == ["venus_mars_pattern", "contradiction_1"]
    assert result.paragraphs == [
        "Психологический механизм. Жизненное проявление. Риск автоматизма.",
        "Второй механизм. Второе проявление. Зрелая форма.",
    ]
