"""BUG51: bounded thematic explanations, not weaker editorial thresholds."""

from __future__ import annotations

import pytest
from tests.unit.test_child.test_content_v2 import _middle_facts

from app.modules.child.assembly import assemble_child_report_payload
from app.modules.child.narrative import (
    MockChildSegmentProvider,
    build_child_section_inputs,
    run_child_segment_generation,
)
from app.modules.child.quality import validate_guidance_facts


@pytest.mark.asyncio
async def test_moderate_signals_reach_their_theme_without_becoming_strengths_or_friction() -> None:
    facts = _middle_facts(contract_version="child-guidance-facts-v4")
    validate_guidance_facts(facts)
    assert facts.strong_matches == facts.friction_points == ()
    inputs = {item.section_key: item for item in build_child_section_inputs(facts)}
    expected = {
        "natural_contact": {"emotional_attunement"},
        "friction_zones": {"boundary_fit", "tempo_fit"},
        "soothing_support": {"soothing_compatibility"},
        "explanation_learning": {"communication_fit", "learning_interaction"},
        "conflict_cycle": {"conflict_pattern"},
        "not_personal": {"autonomy_balance"},
    }
    for key, dimensions in expected.items():
        section = inputs[key]
        assert section.contract_version == "child_section_render_input_v5"
        for dimension in dimensions:
            from app.modules.child.content_v3 import _INTERACTION_OBSERVATIONS

            assert any(_INTERACTION_OBSERVATIONS[dimension] in fact.approved_text for fact in section.owned_facts)
        assert any("нет выраженного перекоса" in fact.approved_text for fact in section.owned_facts)
    rows = [
        await run_child_segment_generation(
            provider=MockChildSegmentProvider(), section_input=item, guidance_facts=facts
        )
        for item in inputs.values()
    ]
    assert not [row.section_key for row in rows if row.status == "failed"]
    by_key = {row.section_key: row for row in rows}
    conflict_content = by_key["conflict_cycle"].content
    intentions_content = by_key["not_personal"].content
    assert conflict_content is not None and "нельзя восстановить конкретный цикл" in conflict_content
    assert intentions_content is not None and "не устанавливает намерения" in intentions_content
    assembly = assemble_child_report_payload(guidance_facts=facts, segment_rows=rows)
    assert assembly["contract_version"] == "child_report_narrative_v5"
    assert "repeated_section_content" not in assembly["quality"]["reason_codes"]
    assert assembly["prompt_version"] == "child-section-prompt-v5"


@pytest.mark.asyncio
async def test_original_v3_v4_inputs_prompts_and_assemblies_remain_frozen() -> None:
    import json
    from pathlib import Path

    from tests.unit.test_child.test_content_v3 import _frozen_facts

    from app.modules.child.narrative import _stable_hash
    from app.modules.child.prompts.v1 import build_child_section_prompt

    fixtures = json.loads((Path(__file__).parent / "fixtures/content_v3_v4_frozen.json").read_text())
    assert len(fixtures) == 2
    for fixture in fixtures:
        facts = _frozen_facts(fixture)
        validate_guidance_facts(facts)
        assert facts.to_payload() == fixture["payload"]
        inputs = build_child_section_inputs(facts, prompt_version=fixture["prompt_version"])
        assert [item.model_dump(mode="json") for item in inputs] == fixture["inputs"]
        assert [_stable_hash({"prompt": build_child_section_prompt(item)}) for item in inputs] == fixture[
            "prompt_hashes"
        ]
        rows = [
            await run_child_segment_generation(
                provider=MockChildSegmentProvider(), section_input=item, guidance_facts=facts
            )
            for item in inputs
        ]
        assert (
            _stable_hash(
                assemble_child_report_payload(
                    guidance_facts=facts, segment_rows=rows, prompt_version=fixture["prompt_version"]
                )
            )
            == fixture["assembly_hash"]
        )


def _signal_facts(score: float = 53, confidence: float = 0.7, *, observations: bool = True):  # type: ignore[no-untyped-def]
    from datetime import date
    from uuid import uuid4

    from tests.unit.test_child.test_context_resolver import _answers, _scores

    from app.modules.child.context_resolver import ResolverAgeSnapshot, resolve_context
    from app.modules.child.guidance_facts import GuidanceInteractionScore, build_guidance_facts

    base = _middle_facts()
    age = ResolverAgeSnapshot(base.age_snapshot_id, "3-6", date(2026, 10, 22), "child-age-mvp-1")
    scores = [{**item, "score": score, "confidence": confidence} for item in _scores()]
    resolution = resolve_context(
        child_profile_id=base.child_id,
        generation_id=base.generation_id,
        questionnaire_session_id=uuid4(),
        age_snapshot=age,
        interaction_scores=scores,
        answers=_answers(),
    )
    if not observations:
        from dataclasses import replace

        from app.modules.child.context_resolver import ResolutionEntry

        resolution = replace(
            resolution,
            confirmations=(),
            contradictions=(),
            unresolved_ambiguities=(
                ResolutionEntry(
                    id="missing-soothing",
                    topic="soothing",
                    dimension="soothing_compatibility",
                    confidence=0,
                    source_refs=(),
                    reason_code="selected_observation_missing",
                    action_code="adult_observes_before_choosing_guidance",
                ),
            ),
        )
    return build_guidance_facts(
        parent_profile_id=base.parent_profile_id,
        child_id=base.child_id,
        generation_id=base.generation_id,
        core_report_version=1,
        age_snapshot=age,
        resolution=resolution,
        interaction_scores=tuple(
            GuidanceInteractionScore(
                str(item["dimension"]),
                score,
                confidence,
                str(item["pattern"]),
                str(item["scoring_version"]),
                (f"child_interaction_scores:{item['id']}:{item['scoring_version']}",),
            )
            for item in scores
        ),
        contract_version="child-guidance-facts-v4",
    )


@pytest.mark.parametrize(
    ("score", "confidence", "state"),
    [
        (35, 0.4, "pronounced_signal"),
        (65, 0.4, "pronounced_signal"),
        (35.01, 0.4, "no_pronounced_skew"),
        (64.99, 0.7, "no_pronounced_skew"),
        (90, 0.39, "ambiguous_signals"),
        (20, 0.2, "ambiguous_signals"),
    ],
)
def test_signal_states_are_bounded_data_not_relaxed_editorial_thresholds(
    score: float, confidence: float, state: str
) -> None:
    facts = _signal_facts(score, confidence)
    validate_guidance_facts(facts)
    assert {item["signal_state"] for item in facts.source_profiles} == {state}
    assert bool(facts.strong_matches) is (score >= 65 and confidence >= 0.4)
    assert bool(facts.friction_points) is (score <= 35 and confidence >= 0.4)
    text = " ".join(fact.approved_text for item in build_child_section_inputs(facts) for fact in item.owned_facts)
    if state == "ambiguous_signals":
        assert "уверенности недостаточно" in text
    if state == "no_pronounced_skew":
        assert "нет выраженного перекоса" in text


def test_missing_observation_and_moderate_measure_are_separate_facts() -> None:
    facts = _signal_facts(observations=False)
    assert {item["signal_state"] for item in facts.source_profiles} == {"no_pronounced_skew"}
    assert any(item["reason_code"] == "selected_observation_missing" for item in facts.recommended_actions)
    sections = {item.section_key: item for item in build_child_section_inputs(facts)}
    soothing = " ".join(item.approved_text for item in sections["soothing_support"].owned_facts)
    assert "нет выбранного наблюдения" in soothing
    assert "нет выраженного перекоса" in soothing


@pytest.mark.parametrize("state", [None, "missing_data", "pronounced_signal", [], 1])
def test_signal_state_forgery_is_rejected_even_with_recomputed_hash(state: object) -> None:
    from app.modules.child.quality import GuidanceFactsQualityError, _guidance_payload_hash

    payload = _signal_facts().to_payload()
    fact = payload["source_profiles"][0]
    if state is None:
        fact.pop("signal_state")
    else:
        fact["signal_state"] = state
    registry = payload["evidence_registry"]
    key = next(key for key, value in registry.items() if value["source_type"] == "guidance_contract")
    digest = _guidance_payload_hash(payload)
    metadata = registry.pop(key)
    registry[f"guidance_contract:{digest}"] = {**metadata, "input_hash": digest}
    with pytest.raises(GuidanceFactsQualityError) as exc:
        validate_guidance_facts(payload)
    assert "invalid_fact_schema" in {issue.code for issue in exc.value.issues}
    assert "invalid_guidance_hash" not in {issue.code for issue in exc.value.issues}


def test_evidence_summary_does_not_label_age_actions_as_missing_interaction_data() -> None:
    from app.modules.child.content_v4 import thematic_evidence_summary

    assert thematic_evidence_summary(_signal_facts(), section_key="current_age") == {}


def test_observation_owned_themes_do_not_mislabel_their_child_need_measure_as_missing() -> None:
    from app.modules.child.content_v4 import thematic_evidence_summary

    facts = _middle_facts(contract_version="child-guidance-facts-v4")
    assert thematic_evidence_summary(facts, section_key="boundaries_rules") == {}
    assert thematic_evidence_summary(facts, section_key="autonomy") == {}


def test_missing_measure_is_not_presented_as_no_pronounced_skew() -> None:
    from dataclasses import replace

    from app.modules.child.content_v4 import thematic_evidence_summary

    facts = replace(_signal_facts(), source_profiles=(), recommended_actions=())
    summary = thematic_evidence_summary(facts, section_key="natural_contact")
    assert summary["evidence_state"] == "missing_data"
    assert "нет" in summary["evidence_note"]


def test_opposing_thematic_measures_are_ambiguous_without_inventing_a_conflict() -> None:
    from dataclasses import replace

    from app.modules.child.content_v4 import thematic_evidence_summary

    facts = _signal_facts(80)
    facts = replace(
        facts,
        source_profiles=tuple(
            {**item, "score": 20} if item["dimension"] == "boundary_fit" else item for item in facts.source_profiles
        ),
    )
    summary = thematic_evidence_summary(facts, section_key="friction_zones")
    assert summary["evidence_state"] == "ambiguous_signals"
    assert "по-разному" in summary["evidence_note"]


def test_new_full_generation_keeps_historical_v3_facts_on_v4_prompt() -> None:
    from app.modules.child.service import _full_generation_prompt_version

    assert (
        _full_generation_prompt_version(_middle_facts(contract_version="child-guidance-facts-v3"))
        == "child-section-prompt-v4"
    )
    assert _full_generation_prompt_version(_signal_facts()) == "child-section-prompt-v5"


@pytest.mark.parametrize(
    ("score", "confidence", "observations", "expected"),
    [
        (53, 0.7, True, "no_pronounced_skew"),
        (90, 0.2, True, "ambiguous_signals"),
        (70, 0.7, True, "pronounced_signal"),
        (53, 0.7, False, "missing_data"),
    ],
)
@pytest.mark.asyncio
async def test_thematic_evidence_states_reach_presentation_and_pdf(
    score: float, confidence: float, observations: bool, expected: str
) -> None:
    from datetime import date
    from uuid import uuid4

    from app.modules.child import models
    from app.modules.child.pdf import render_child_report_html
    from app.modules.child.presentation import compose_child_report_presentation
    from app.modules.child.prompts.v1 import SECTION_METADATA

    facts = _signal_facts(score, confidence, observations=observations)
    report = models.ChildReport(
        id=uuid4(),
        child_profile_id=facts.child_id,
        generation_id=facts.generation_id,
        version=1,
        prompt_version="child-section-prompt-v5",
        presentation_manifest={
            "contract_version": "child_report_presentation_v1",
            "section_order": list(SECTION_METADATA),
            "age_snapshot_id": str(facts.age_snapshot_id),
        },
    )
    age = models.ChildAgeSnapshot(
        id=facts.age_snapshot_id,
        child_profile_id=facts.child_id,
        as_of_date=date(2026, 10, 22),
        age_years=5,
        age_months=4,
        age_days=1,
        age_stage="3-6",
        age_rules_version="child-age-mvp-1",
        input_hash="a" * 64,
    )
    rows = [
        await run_child_segment_generation(
            provider=MockChildSegmentProvider(), section_input=item, guidance_facts=facts
        )
        for item in build_child_section_inputs(facts)
    ]
    assert all(row.status != "failed" for row in rows)
    presentation = compose_child_report_presentation(
        report=report,
        facts=facts,
        age_snapshot=age,
        segment_rows=rows,
        generation_status="ready",
        current_local_date=date(2026, 10, 22),
    )
    soothing = next(item for item in presentation["sections"] if item["key"] == "soothing_support")
    assert soothing["evidence_state"] == expected
    assert soothing["evidence_note"]
    assert soothing["evidence_note"] in render_child_report_html(presentation)
    indicators = presentation["technical_basis"]["source_indicators"]
    assert all("signal_state" in item for item in indicators if item["source_kind"] == "interaction")
