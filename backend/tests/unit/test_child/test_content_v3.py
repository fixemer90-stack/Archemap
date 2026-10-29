# ruff: noqa: RUF001
"""BUG50 scoped composition and frozen historical contract regressions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest
from tests.unit.test_child.test_content_v2 import _middle_facts

from app.modules.child.age_resolver import AgeStage
from app.modules.child.assembly import assemble_child_report_payload
from app.modules.child.guidance_facts import ChildGuidanceFacts, _freeze
from app.modules.child.narrative import (
    MockChildSegmentProvider,
    _stable_hash,
    build_child_section_inputs,
    prompt_version_for_input,
    run_child_segment_generation,
)
from app.modules.child.prompts.v1 import build_child_section_prompt
from app.modules.child.quality import validate_guidance_facts


def _frozen_facts(fixture: dict[str, Any]) -> ChildGuidanceFacts:
    payload = fixture["payload"]
    return ChildGuidanceFacts(
        contract_version=payload["contract_version"],
        parent_profile_id=UUID(payload["parent_profile_id"]),
        child_id=UUID(payload["child_id"]),
        generation_id=UUID(fixture["generation_id"]),
        core_report_version=payload["core_report_version"],
        age_snapshot_id=UUID(payload["age_snapshot_id"]),
        age_stage=cast(AgeStage, fixture["age_stage"]),
        input_hash=fixture["input_hash"],
        evidence_registry=_freeze(payload["evidence_registry"]),
        source_profiles=_freeze(payload.get("source_profiles", [])),
        **{
            family: _freeze(payload[family])
            for family in (
                "strong_matches",
                "friction_points",
                "parent_strengths",
                "compensation_areas",
                "recommended_actions",
                "avoid_patterns",
                "confidence_markers",
            )
        },
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("profile_score", [20.0, 53.0, 78.0])
@pytest.mark.parametrize("low_interaction", [False, True])
async def test_ordinary_full_mixed_sources_keep_every_dimension_and_local_uncertainty(
    profile_score: float, low_interaction: bool
) -> None:
    from datetime import date
    from uuid import uuid4

    from tests.unit.test_child.test_context_resolver import _answers, _scores

    from app.modules.child.context_resolver import ResolverAgeSnapshot, resolve_context
    from app.modules.child.guidance_facts import GuidanceInteractionScore, GuidanceProfileScore, build_guidance_facts
    from app.modules.child.scoring.types import ChildNeedDimension, ParentStyleDimension

    base = _middle_facts()
    age = ResolverAgeSnapshot(base.age_snapshot_id, "3-6", date(2026, 10, 22), "child-age-mvp-1")
    scores = _scores()
    if low_interaction:
        scores[0]["confidence"] = 0.2
    facts = build_guidance_facts(
        parent_profile_id=base.parent_profile_id,
        child_id=base.child_id,
        generation_id=base.generation_id,
        core_report_version=1,
        age_snapshot=age,
        resolution=resolve_context(
            child_profile_id=base.child_id,
            generation_id=base.generation_id,
            questionnaire_session_id=uuid4(),
            age_snapshot=age,
            interaction_scores=scores,
            answers=_answers(),
        ),
        interaction_scores=tuple(
            GuidanceInteractionScore(
                str(item["dimension"]),
                float(str(item["score"])),
                float(str(item["confidence"])),
                str(item["pattern"]),
                str(item["scoring_version"]),
                (f"child_interaction_scores:{item['id']}:{item['scoring_version']}",),
            )
            for item in scores
        ),
        profile_scores=tuple(
            GuidanceProfileScore(
                kind,
                dimension.value,
                profile_score,
                0.2 if index == 0 else 0.7,
                version,
                (f"{table}:{uuid4()}:{version}",),
            )
            for kind, dimensions, version, table in (
                ("parent_style", tuple(ParentStyleDimension), "parent-style-mvp-2", "child_parent_style_scores"),
                ("child_needs", tuple(ChildNeedDimension), "child-needs-mvp-1", "child_need_scores"),
            )
            for index, dimension in enumerate(dimensions)
        ),
        contract_version="child-guidance-facts-v3",
    )
    validate_guidance_facts(facts)
    inputs = build_child_section_inputs(facts)
    rows = [
        await run_child_segment_generation(
            provider=MockChildSegmentProvider(), section_input=item, guidance_facts=facts
        )
        for item in inputs
    ]
    assert all(row.status in {"ready", "not_applicable"} for row in rows)
    assembly = assemble_child_report_payload(guidance_facts=facts, segment_rows=rows)
    assert "repeated_section_content" not in assembly["quality"]["reason_codes"]
    assert len(facts.source_profiles) == 26
    resource_caveat = "выделение ресурса в расчёте не доказывает успеха в семье"
    assert " ".join(row.content or "" for row in rows).lower().count(resource_caveat) <= 1
    all_facts = {
        fact["id"]: fact
        for family in (
            facts.source_profiles,
            facts.strong_matches,
            facts.friction_points,
            facts.recommended_actions,
            facts.compensation_areas,
            facts.avoid_patterns,
        )
        for fact in family
    }
    evidence = {ref for row in rows for fact_id in row.evidence_refs for ref in all_facts[fact_id]["evidence_refs"]}
    assert {ref for fact in facts.source_profiles for ref in fact["evidence_refs"]} <= evidence
    for section in inputs:
        for fact in section.owned_facts:
            if fact.conditional:
                assert "возможно" in fact.approved_text.casefold()
                if fact.family == "source_profiles":
                    assert "недостаточно оснований" in fact.approved_text


@pytest.mark.asyncio
async def test_original_v1_v2_inputs_prompts_and_assemblies_remain_frozen() -> None:
    fixtures = json.loads((Path(__file__).parent / "fixtures/content_v1_v2_frozen.json").read_text())
    for fixture in fixtures:
        facts = _frozen_facts(fixture)
        validate_guidance_facts(facts)
        assert facts.to_payload() == fixture["payload"]
        inputs = build_child_section_inputs(facts)
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
            _stable_hash(assemble_child_report_payload(guidance_facts=facts, segment_rows=rows))
            == fixture["assembly_hash"]
        )


@pytest.mark.asyncio
async def test_v3_is_an_explicit_full_content_contract_through_assembly() -> None:
    facts = _middle_facts(contract_version="child-guidance-facts-v3")
    validate_guidance_facts(facts)
    inputs = build_child_section_inputs(facts)
    assert all(item.contract_version == "child_section_render_input_v3" for item in inputs)
    assert {prompt_version_for_input(item) for item in inputs} == {"child-section-prompt-v3"}
    assert all("child-section-prompt-v3" in build_child_section_prompt(item) for item in inputs)
    rows = [
        await run_child_segment_generation(
            provider=MockChildSegmentProvider(), section_input=item, guidance_facts=facts
        )
        for item in inputs
    ]
    assembly = assemble_child_report_payload(guidance_facts=facts, segment_rows=rows)
    assert assembly["status"] == "ready"
    assert assembly["contract_version"] == "child_report_narrative_v3"
    assert assembly["prompt_version"] == "child-section-prompt-v3"
    assert len(facts.source_profiles) == 19


@pytest.mark.asyncio
async def test_v3_composes_shared_caveats_once_without_losing_local_evidence() -> None:
    from app.modules.child.narrative import _PROFILE_SCALE_CONTEXT

    facts = _middle_facts(contract_version="child-guidance-facts-v3")
    inputs = build_child_section_inputs(facts)
    rows = [
        await run_child_segment_generation(
            provider=MockChildSegmentProvider(), section_input=item, guidance_facts=facts
        )
        for item in inputs
    ]
    assert all(row.status in {"ready", "not_applicable"} for row in rows)
    body = " ".join(row.content or "" for row in rows)
    caveat = "Это не оценка способностей и не фиксированная черта ребёнка"
    old_middle = (
        "Расчёт находится между полюсами шкалы и не даёт оснований выбрать один способ как устойчиво подходящий"
    )
    old_reason = "Расчёт и наблюдение не дают однозначного основания для направленного вывода"
    assert body.count(caveat) == 1
    assert body.count(old_middle) <= 1
    assert body.count(old_reason) <= 1
    assert body.count("сопоставить с повседневными эпизодами") <= 1
    assert caveat in (rows[0].content or "")  # report-wide method, not per-profile boilerplate
    cited = {reference for row in rows for reference in row.evidence_refs}
    assert {fact["id"] for fact in facts.source_profiles} <= cited
    assert {fact["id"] for fact in facts.recommended_actions} <= cited
    for profile in facts.source_profiles:
        if profile["source_kind"] != "interaction":
            assert _PROFILE_SCALE_CONTEXT[str(profile["dimension"])] in body
    adjustments = next(row for row in rows if row.section_key == "conscious_adjustments")
    assert "лёгких и трудных переключений" in (adjustments.content or "")
    assert (
        "repeated_section_content"
        not in assemble_child_report_payload(guidance_facts=facts, segment_rows=rows)["quality"]["reason_codes"]
    )


@pytest.mark.parametrize("same_section", [False, True])
@pytest.mark.parametrize(
    "repeated",
    [
        "Это не оценка способностей и не фиксированная черта ребёнка",
        "выделение ресурса в расчёте не доказывает успеха в семье",
    ],
)
def test_v3_quality_detects_boilerplate_inside_distinct_claims(same_section: bool, repeated: str) -> None:
    from app.modules.child.assembly import assess_child_report_quality

    sections = [
        {"section_key": "parent_style", "body": f"Первая шкала: {repeated}; наблюдайте структуру."},
        {"section_key": "child_interaction_needs", "body": f"Другая шкала: {repeated}; наблюдайте ободрение."},
    ]
    if same_section:
        sections[0]["body"] += " " + sections.pop()["body"]
    quality = assess_child_report_quality(
        sections=sections, omitted_sections=[], failed_sections=[], missing_sections=[]
    )
    assert quality["status"] == "limited"
    assert "repeated_section_content" in quality["reason_codes"]
    assert "parent_style" in quality["repeated_sections"]


def test_v3_quality_allows_single_scoped_method_and_legitimate_topic_overlap() -> None:
    from app.modules.child.assembly import assess_child_report_quality

    quality = assess_child_report_quality(
        sections=[
            {"section_key": "how_to_use", "body": "Это не оценка способностей и не фиксированная черта ребёнка."},
            {"section_key": "parent_style", "body": "Возможно, взрослый может наблюдать структуру правил."},
            {"section_key": "boundaries_rules", "body": "Возможно, взрослый может объяснять правило спокойно."},
        ],
        omitted_sections=[],
        failed_sections=[],
        missing_sections=[],
    )
    assert quality["status"] == "ready"


@pytest.mark.asyncio
@pytest.mark.parametrize("fails", [False, True])
async def test_v3_persists_only_bounded_observed_usage_even_after_provider_failure(fails: bool) -> None:
    from app.modules.child.narrative import ChildSectionRenderInput
    from app.modules.llm.usage import record_provider_attempt, record_provider_response

    class ObservedProvider(MockChildSegmentProvider):
        async def generate_segment(self, *, prompt: str, section_input: ChildSectionRenderInput) -> dict[str, Any]:
            record_provider_attempt()
            record_provider_response(
                {"usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10}, "private": "excluded"}
            )
            if fails:
                raise RuntimeError("private provider error")
            return await super().generate_segment(prompt=prompt, section_input=section_input)

    for version in ("child-guidance-facts-v2", "child-guidance-facts-v3"):
        facts = _middle_facts(contract_version=version)
        row = await run_child_segment_generation(
            provider=ObservedProvider(), section_input=build_child_section_inputs(facts)[0], guidance_facts=facts
        )
        assert row.status == ("failed" if fails else "ready")
        if version.endswith("v2"):
            assert "provider_usage" not in row.diagnostics
        else:
            assert row.diagnostics["provider_usage"] == {
                "http_attempts": 1,
                "responses_with_usage": 1,
                "responses_without_usage": 0,
                "prompt_tokens": 7,
                "completion_tokens": 3,
                "total_tokens": 10,
            }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_usage",
    [
        None,
        [],
        {"private": "must not publish"},
        {"http_attempts": True, "responses_with_usage": 0, "responses_without_usage": 0},
        {"http_attempts": 0, "responses_with_usage": 1, "responses_without_usage": 0},
        {
            "http_attempts": 1,
            "responses_with_usage": 1,
            "responses_without_usage": 0,
            "prompt_tokens": 7,
            "completion_tokens": 3,
            "total_tokens": 11,
        },
        {
            "http_attempts": 1,
            "responses_with_usage": 1,
            "responses_without_usage": 0,
            "prompt_tokens": 7,
            "completion_tokens": 3,
            "total_tokens": 10,
            "prompt_cache_hit_tokens": 8,
            "prompt_cache_miss_tokens": 0,
        },
    ],
)
async def test_v3_assembly_rejects_hostile_usage_before_publication(bad_usage: Any) -> None:
    from app.modules.child.narrative import ChildNarrativeValidationError

    facts = _middle_facts(contract_version="child-guidance-facts-v3")
    row = await run_child_segment_generation(
        provider=MockChildSegmentProvider(), section_input=build_child_section_inputs(facts)[0], guidance_facts=facts
    )
    row.diagnostics = {**row.diagnostics, "provider_usage": bad_usage}
    with pytest.raises(ChildNarrativeValidationError, match="provider usage"):
        assemble_child_report_payload(guidance_facts=facts, segment_rows=[row])


@pytest.mark.asyncio
async def test_v3_crash_shaped_intent_can_publish_partial_without_fabricated_usage() -> None:
    from uuid import uuid4

    from app.modules.child.narrative import build_child_segment_intent

    facts = _middle_facts(contract_version="child-guidance-facts-v3")
    row = build_child_segment_intent(
        provider=MockChildSegmentProvider(),
        section_input=build_child_section_inputs(facts)[0],
        guidance_facts=facts,
        lifecycle_token=uuid4(),
    )
    row.status = "failed"
    row.error_code = "child_narrative_provider_outcome_unknown"
    row.diagnostics = {**row.diagnostics, "attempts": 1, "error_type": "provider_error"}
    assert "provider_usage" not in row.diagnostics
    assembly = assemble_child_report_payload(guidance_facts=facts, segment_rows=[row])
    assert assembly["status"] == "partial"
    assert assembly["failed_sections"] == [row.section_key]


@pytest.mark.asyncio
async def test_v3_profile_only_sections_remain_safe_without_invented_observations() -> None:
    from tests.unit.test_child.test_content_v2 import _current_facts

    facts = _current_facts(contract_version="child-guidance-facts-v3")
    rows = [
        await run_child_segment_generation(
            provider=MockChildSegmentProvider(), section_input=item, guidance_facts=facts
        )
        for item in build_child_section_inputs(facts)
    ]
    assert all(row.status in {"ready", "not_applicable"} for row in rows)


@pytest.mark.parametrize("helper", ["fact_families", "section_contracts"])
def test_version_helpers_do_not_fall_back_to_v1_for_unknown_versions(helper: str) -> None:
    from app.modules.child import quality

    with pytest.raises(ValueError, match="Unsupported"):
        getattr(quality, helper)("child-guidance-facts-v99")


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["unsupported_conditional", "missing_conditional_flag", "cross_owned_fact"])
async def test_v3_grounding_and_ownership_cannot_be_laundered_by_uncertainty(mutation: str) -> None:
    from tests.unit.test_child.test_content_v2 import _current_facts
    from tests.unit.test_child.test_narrative_pipeline import _output

    from app.modules.child.narrative import ChildNarrativeValidationError, validate_segment_output
    from app.modules.child.safety import ChildSafetyViolation, NarrativeSectionCandidate, validate_child_narrative

    facts = _current_facts(parent_confidence=0.2, contract_version="child-guidance-facts-v3")
    sections = {item.section_key: item for item in build_child_section_inputs(facts)}
    if mutation == "cross_owned_fact":
        praise_id = next(fact["id"] for fact in facts.source_profiles if fact["dimension"] == "recognition")
        parent_id = next(fact["id"] for fact in facts.source_profiles if fact["source_kind"] == "parent_style")
        with pytest.raises(ChildSafetyViolation) as rejected:
            validate_child_narrative(
                NarrativeSectionCandidate(
                    section_key="praise_recognition",
                    content="Возможно, взрослый может наблюдать.",
                    fact_refs=(praise_id, parent_id),
                ),
                guidance_facts=facts,
            )
        assert "section_fact_ownership" in rejected.value.categories
        return
    section = sections["parent_style"]
    assert section.owned_facts[0].conditional
    output = _output(section)
    claim = output.claims[0].model_copy(
        update={"text": "Возможно, взрослый может считать ребёнка прирождённым лидером."}
        if mutation == "unsupported_conditional"
        else {"conditional": False}
    )
    output = output.model_copy(update={"claims": [claim], "body": claim.text})
    with pytest.raises(ChildNarrativeValidationError, match="approved"):
        validate_segment_output(output=output, section_input=section, guidance_facts=facts)
