# ruff: noqa: RUF001
"""RED tests for E14 S04 staged LLM contracts and prompt family."""

from __future__ import annotations

from app.modules.report_narratives.prompts import (
    STAGED_SELF_PROMPT_VERSIONS,
    build_stage_prompt,
    load_prompt_template,
)
from app.modules.report_narratives.schemas import (
    AssemblyCheck,
    DeepNatalSynthesis,
    DevelopmentSectionOutput,
    EmotionalSectionOutput,
    HouseScenariosSectionOutput,
    IdentitySectionOutput,
    NarrativePlan,
    RelationshipSectionOutput,
)


def _fake_synthesis() -> DeepNatalSynthesis:
    return DeepNatalSynthesis.model_validate(
        {
            "contract_version": "deep_natal_synthesis_v1",
            "source_chart_snapshot_id": "chart:test",
            "evidence_map": {
                "sun_virgo_house_9": {
                    "id": "sun_virgo_house_9",
                    "label": "Солнце в Деве в 9 доме",
                    "kind": "planet_placement",
                    "source": "chart.planets",
                    "meaning": "Идентичность строится через систему смысла.",
                },
                "moon_opposition_saturn": {
                    "id": "moon_opposition_saturn",
                    "label": "Луна оппозиция Сатурн",
                    "aspect_type": "opposition",
                    "source": "chart.aspects",
                    "meaning": "Чувства быстро встречают внутренний контроль.",
                },
            },
            "ranked_aspects": [
                {
                    "id": "moon_opposition_saturn",
                    "label": "Луна оппозиция Сатурн",
                    "weight": 0.92,
                    "evidence_ids": ["moon_opposition_saturn"],
                    "section_targets": ["emotions_and_communication", "development"],
                }
            ],
            "aspect_patterns": [
                {
                    "id": "saturn_boundary_pattern",
                    "title": "Контроль и уязвимость",
                    "aspect_ids": ["moon_opposition_saturn"],
                    "planets": ["Moon", "Saturn"],
                    "pattern_type": "tension",
                    "psychological_mechanism": "Переживание быстро проходит через фильтр внутреннего контроля.",
                    "life_manifestation": "Человек долго держит важное внутри.",
                    "risk": "Сдерживание может выглядеть как холодность.",
                    "mature_expression": "Сначала назвать переживание, потом решать форму выражения.",
                    "section_targets": ["emotions_and_communication", "development"],
                    "evidence_ids": ["moon_opposition_saturn"],
                    "weight": 0.92,
                }
            ],
            "house_axis_patterns": [
                {
                    "id": "house_axis_house_scenario_sun_9",
                    "title": "Смысл как ось идентичности",
                    "axis": "Дом 9",
                    "mechanism": "Нужно собрать из опыта систему смысла.",
                    "manifestation": "Человек ищет позицию, а не просто впечатления.",
                    "evidence_ids": ["sun_virgo_house_9"],
                    "section_targets": ["main_formula", "world_perception"],
                }
            ],
            "planet_roles": [
                {
                    "id": "planet_role_sun_virgo_house_9",
                    "title": "Солнце в Деве в 9 доме",
                    "function": "Собирает идентичность через анализ и систему взглядов.",
                    "influence": "Даёт потребность занимать обоснованную позицию.",
                    "section_targets": ["main_formula"],
                    "evidence_ids": ["sun_virgo_house_9"],
                }
            ],
            "chart_dynamics": [
                {
                    "id": "chart_dynamic_moon_saturn_regulation",
                    "title": "Напряжение между чувственным импульсом и внутренним контролем",
                    "mechanism": "Реакция быстро встречает внутреннюю проверку.",
                    "tension": "Хочется выразиться и одновременно удержать управление.",
                    "compensation": "Сначала назвать переживание, потом выбирать форму.",
                    "section_targets": ["emotions_and_communication", "development"],
                    "evidence_ids": ["moon_opposition_saturn"],
                }
            ],
            "contradictions": [
                {
                    "id": "contradiction_moon_saturn_expression_vs_control",
                    "title": "Выразить чувство или удержать контроль",
                    "tension": "Выражение и контроль сталкиваются одновременно.",
                    "manifestation": "Снаружи это выглядит как сдержанная включённость.",
                    "mature_expression": "Чувство получает форму, а не подавление.",
                    "evidence_ids": ["moon_opposition_saturn"],
                }
            ],
            "maturity_levels": {
                "low": {
                    "title": "Реактивная защита",
                    "body": "Напряжение проживается автоматично и закрывает контакт.",
                    "evidence_ids": ["moon_opposition_saturn"],
                },
                "medium": {
                    "title": "Осознавание без устойчивости",
                    "body": "Человек уже замечает паттерн, но ещё срывается в старую защиту.",
                    "evidence_ids": ["moon_opposition_saturn"],
                },
                "high": {
                    "title": "Управляемая глубина",
                    "body": "Переживание переводится в выбранный ритм и форму контакта.",
                    "evidence_ids": ["moon_opposition_saturn"],
                },
            },
            "calibration_hypotheses": [
                {
                    "id": "calibration_chart_dynamic_moon_saturn_regulation",
                    "hypothesis": "Когда напряжение растёт, замечаете ли вы, что сначала сдерживаете реакцию?",
                    "answer_type": "scale_1_5",
                    "evidence_ids": ["moon_opposition_saturn"],
                }
            ],
        }
    )


def test_staged_prompt_versions_are_file_backed_and_guardrailed() -> None:
    required_versions = {
        "plan": "self_plan_v1",
        "identity": "self_section_identity_v1",
        "emotional": "self_section_emotional_v1",
        "relationships": "self_section_relationships_v1",
        "development": "self_section_development_v1",
        "house_scenarios": "self_section_house_scenarios_v1",
        "assembly": "self_assemble_v1",
    }
    assert required_versions == STAGED_SELF_PROMPT_VERSIONS

    for version in required_versions.values():
        template = load_prompt_template(version).lower()
        assert "renderer/synthesizer" in template or "renderer and synthesizer" in template
        assert "not calculator" in template
        assert "use only provided evidence ids" in template
        assert "no markdown" in template
        assert "no unsupported aspects" in template
        assert "no career deep dive" in template
        assert "no diagnostic" in template
        assert "no fatalistic" in template


def test_stage_prompt_builders_include_only_relevant_synthesis_slices() -> None:
    synthesis = _fake_synthesis()

    plan_prompt = build_stage_prompt("plan", synthesis=synthesis)
    assert "DeepNatalSynthesis" in plan_prompt
    assert "chart_dynamic_moon_saturn_regulation" in plan_prompt

    identity_prompt = build_stage_prompt("identity", synthesis=synthesis)
    assert "planet_roles" in identity_prompt
    assert "house_axis_patterns" in identity_prompt
    assert "ranked_aspects" not in identity_prompt

    emotional_prompt = build_stage_prompt("emotional", synthesis=synthesis)
    assert "chart_dynamics" in emotional_prompt
    assert "contradictions" in emotional_prompt
    assert "planet_roles" not in emotional_prompt

    assembly_prompt = build_stage_prompt(
        "assembly",
        synthesis=synthesis,
        stage_outputs={
            "identity": {"section_id": "identity", "paragraphs": ["..."], "evidence_ids": ["sun_virgo_house_9"]},
            "emotional": {"section_id": "emotional", "paragraphs": ["..."], "evidence_ids": ["moon_opposition_saturn"]},
        },
    )
    assert "stage_outputs" in assembly_prompt
    assert "DeepNatalSynthesis" not in assembly_prompt


def test_stage_output_schemas_validate_minimal_contracts() -> None:
    plan = NarrativePlan.model_validate(
        {
            "prompt_version": "self_plan_v1",
            "sections": [
                {
                    "section_id": "identity",
                    "title": "Как собирается ваша идентичность",
                    "required_evidence_ids": ["sun_virgo_house_9"],
                    "focus": "Смысл и позиция как ось личности.",
                },
                {
                    "section_id": "emotional",
                    "title": "Как вы переживаете и выражаете напряжение",
                    "required_evidence_ids": ["moon_opposition_saturn"],
                    "focus": "Чувство проходит через внутренний контроль.",
                },
            ],
            "global_guardrails": ["use only provided evidence ids", "no career deep dive"],
            "assembly_notes": "Собрать единый Self narrative без повторов.",
        }
    )
    assert len(plan.sections) == 2

    identity = IdentitySectionOutput.model_validate(
        {
            "section_id": "identity",
            "title": "Как собирается ваша идентичность",
            "paragraphs": ["Вы не просто ищете впечатления — вам важно занять обоснованную позицию."],
            "evidence_ids": ["sun_virgo_house_9"],
            "covered_pattern_ids": ["house_axis_house_scenario_sun_9"],
        }
    )
    emotional = EmotionalSectionOutput.model_validate(
        {
            "section_id": "emotional",
            "title": "Как вы переживаете и выражаете напряжение",
            "paragraphs": ["Сильная реакция быстро встречает внутреннюю проверку на уместность."],
            "evidence_ids": ["moon_opposition_saturn"],
            "covered_pattern_ids": ["saturn_boundary_pattern"],
        }
    )
    relationships = RelationshipSectionOutput.model_validate(
        {
            "section_id": "relationships",
            "title": "Как вы входите в близость",
            "paragraphs": ["В близости вам важны и взаимность, и ощущение безопасности."],
            "evidence_ids": ["moon_opposition_saturn"],
            "covered_pattern_ids": ["saturn_boundary_pattern"],
        }
    )
    development = DevelopmentSectionOutput.model_validate(
        {
            "section_id": "development",
            "title": "Во что эта динамика может вырасти",
            "paragraphs": ["Зрелость приходит, когда чувство получает форму до самоподавления."],
            "evidence_ids": ["moon_opposition_saturn"],
            "covered_pattern_ids": ["saturn_boundary_pattern"],
        }
    )
    houses = HouseScenariosSectionOutput.model_validate(
        {
            "section_id": "house_scenarios",
            "title": "Где это особенно видно в жизни",
            "paragraphs": ["Тема смысла особенно заметна в выборе среды обучения и мировоззрения."],
            "evidence_ids": ["sun_virgo_house_9"],
            "covered_pattern_ids": ["house_axis_house_scenario_sun_9"],
        }
    )
    assembly = AssemblyCheck.model_validate(
        {
            "duplicate_claim_ids": [],
            "missing_required_evidence_ids": [],
            "tone_notes": ["Тон плотный и не скатывается в общий гороскоп."],
            "needs_retry": False,
        }
    )

    assert identity.section_id == "identity"
    assert emotional.section_id == "emotional"
    assert relationships.section_id == "relationships"
    assert development.section_id == "development"
    assert houses.section_id == "house_scenarios"
    assert assembly.needs_retry is False
