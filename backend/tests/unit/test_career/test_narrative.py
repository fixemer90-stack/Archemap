from __future__ import annotations

import uuid

import pytest

from app.modules.career.interpretation_facts import CareerInterpretationFacts
from app.modules.career.narrative import (
    CAREER_PROMPT_VERSION,
    CareerNarrativeValidationError,
    MockCareerSegmentProvider,
    StructuredCareerSegmentProviderAdapter,
    assemble_career_report_row,
    build_career_section_inputs,
    build_deterministic_career_report_row,
    build_segment_prompt,
    run_career_segment_generation,
    validate_segment_output,
)
from app.modules.career.narrative_schemas import CareerSegmentOutput


def _facts() -> CareerInterpretationFacts:
    profile_id = uuid.uuid4()
    chart_id = uuid.uuid4()
    dimension = {
        "fact_key": "dimension:systems_thinking",
        "dimension": "systems_thinking",
        "score": 88,
        "confidence": 0.9,
        "scoring_version": "career-mvp-1",
        "evidence_refs": [f"natal_fact:{uuid.uuid4()}"],
        "conditional_language_required": False,
    }
    role = {
        "fact_key": "role:architecture",
        "role_family_key": "architecture",
        "score": 84,
        "confidence": 0.86,
        "category": "strong_match",
        "reasons": ["dimension:systems_thinking"],
        "tensions": ["tension:context_fit_requires_validation"],
        "requirements": ["context:validate_against_real_role_scope"],
        "profession_examples": ["Solution Architect"],
        "catalog_version": "career-role-catalog-1",
    }
    sections = {}
    section_keys = (
        "professional_summary", "work_style", "strengths", "decision_making",
        "leadership_and_influence", "optimal_environment", "risk_environment",
        "career_archetypes", "role_families", "career_paths",
    )
    for key in section_keys:
        owned = ["role:architecture"] if key == "role_families" else ["dimension:systems_thinking"]
        sections[key] = {
            "section_key": key,
            "owned_fact_keys": owned,
            "reference_fact_keys": [],
            "forbidden_fact_keys": [
                "dimension:systems_thinking" if owned[0] == "role:architecture" else "role:architecture"
            ],
        }
    return CareerInterpretationFacts.model_validate({
        "profile_id": profile_id,
        "chart_id": chart_id,
        "scoring_version": "career-mvp-1",
        "top_dimensions": [dimension],
        "low_dimensions": [],
        "career_archetypes": [],
        "preferred_environment": [],
        "risk_environment": [],
        "confirmed_traits": [],
        "contradictions": [],
        "user_preferences": ["expert"],
        "context_constraints": ["experience:senior"],
        "role_matches": [role],
        "career_paths": [],
        "section_contracts": sections,
    })


def test_section_inputs_are_bounded_and_prompt_is_one_section_only() -> None:
    facts = _facts()
    inputs = build_career_section_inputs(facts)
    role_input = next(item for item in inputs if item.section_key == "role_families")

    assert len(inputs) == 10
    assert [item["fact_key"] for item in role_input.owned_facts] == ["role:architecture"]
    assert role_input.reference_facts == []
    assert "dimension:systems_thinking" in role_input.forbidden_fact_keys
    payload = role_input.model_dump(mode="json")
    assert "raw_chart" not in str(payload)
    assert "raw_answers" not in str(payload)
    prompt = build_segment_prompt(role_input)
    assert "role_families" in prompt
    assert "one section" in prompt.lower()
    assert "role:architecture" in prompt
    assert '"dimension": "systems_thinking"' not in prompt


@pytest.mark.asyncio
async def test_mock_provider_and_runner_persist_same_typed_contract() -> None:
    facts = _facts()
    section_input = build_career_section_inputs(facts)[0]
    row = await run_career_segment_generation(
        provider=MockCareerSegmentProvider(),
        section_input=section_input,
        career_profile_id=facts.profile_id,
        chart_id=facts.chart_id,
        generation_id=uuid.uuid4(),
    )

    output = CareerSegmentOutput.model_validate(row.output_payload)
    assert row.status == "ready"
    assert row.prompt_version == CAREER_PROMPT_VERSION
    assert row.input_payload["contract_version"] == "career_section_render_input_v1"
    assert output.section_key == section_input.section_key
    assert set(output.cited_fact_keys) == set(section_input.owned_fact_keys)


@pytest.mark.asyncio
async def test_structured_provider_adapter_uses_career_output_contract() -> None:
    facts = _facts()
    section_input = build_career_section_inputs(facts)[0]

    class StructuredProvider:
        async def generate_structured(self, *, prompt, narrative_input, schema):
            assert prompt
            assert narrative_input is section_input
            assert schema is CareerSegmentOutput
            return schema(
                section_key=section_input.section_key,
                title=section_input.section_title,
                body="Рабочая механика проявляется в системном анализе задач и требует проверки на контексте роли.",
                cited_fact_keys=list(section_input.owned_fact_keys),
            )

    adapter = StructuredCareerSegmentProviderAdapter(
        provider=StructuredProvider(),
        provider_name="test-provider",
        model_name="test-model",
    )
    row = await run_career_segment_generation(
        provider=adapter,
        section_input=section_input,
        career_profile_id=facts.profile_id,
        chart_id=facts.chart_id,
        generation_id=uuid.uuid4(),
    )

    assert row.status == "ready"
    assert row.provider == "test-provider"
    assert row.model_version == "test-model"
    CareerSegmentOutput.model_validate(row.output_payload)


def test_quality_gates_reject_generic_overclaim_and_profession_prescription() -> None:
    section_input = build_career_section_inputs(_facts())[0]
    bad_bodies = (
        "Вы уникальны, раскройте свой потенциал и просто найдите баланс.",
        "Эта роль гарантирует высокий доход и успешное трудоустройство.",
        "Вам нужно стать Solution Architect.",
    )
    for body in bad_bodies:
        output = CareerSegmentOutput(
            section_key=section_input.section_key,
            title="Раздел",
            body=body,
            cited_fact_keys=list(section_input.owned_fact_keys),
        )
        with pytest.raises(CareerNarrativeValidationError):
            validate_segment_output(output=output, section_input=section_input)


@pytest.mark.asyncio
async def test_provider_failure_keeps_deterministic_report_and_section_retry_is_isolated() -> None:
    facts = _facts()
    generation_id = uuid.uuid4()
    report = build_deterministic_career_report_row(
        facts=facts,
        generation_id=generation_id,
        idempotency_key="career-report-1",
        version=1,
    )

    class FailingProvider:
        provider_name = "failing"
        model_name = "test"

        async def generate_segment(self, *, prompt, section_input):
            raise RuntimeError("provider secret detail")

    section_input = build_career_section_inputs(facts)[0]
    failed = await run_career_segment_generation(
        provider=FailingProvider(),
        section_input=section_input,
        career_profile_id=facts.profile_id,
        chart_id=facts.chart_id,
        generation_id=generation_id,
    )
    assembled = assemble_career_report_row(report=report, segment_rows=[failed])

    assert failed.status == "failed"
    assert failed.error == "career_provider_failure"
    assert assembled.status == "narrative_failed"
    assert assembled.deterministic_payload == report.deterministic_payload
    assert assembled.narrative_payload["sections"] == []

    retried = await run_career_segment_generation(
        provider=MockCareerSegmentProvider(),
        section_input=section_input,
        career_profile_id=facts.profile_id,
        chart_id=facts.chart_id,
        generation_id=generation_id,
    )
    assert retried.section_key == failed.section_key
    assert retried.status == "ready"
    assert report.deterministic_payload == assembled.deterministic_payload


@pytest.mark.asyncio
async def test_mock_provider_generates_distinct_sections_that_assemble_to_ready() -> None:
    facts = _facts()
    generation_id = uuid.uuid4()
    report = build_deterministic_career_report_row(
        facts=facts,
        generation_id=generation_id,
        idempotency_key="career-report-all-sections",
        version=1,
    )
    rows = [
        await run_career_segment_generation(
            provider=MockCareerSegmentProvider(),
            section_input=section_input,
            career_profile_id=facts.profile_id,
            chart_id=facts.chart_id,
            generation_id=generation_id,
        )
        for section_input in build_career_section_inputs(facts)
    ]

    assembled = assemble_career_report_row(report=report, segment_rows=rows)

    assert assembled.status == "ready"
    assert len(assembled.narrative_payload["sections"]) == 10
    assert len({section["body"] for section in assembled.narrative_payload["sections"]}) == 10
