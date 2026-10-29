"""Synthetic issue #50 regressions; no production child data."""

from datetime import date
from typing import Any

import pytest
from tests.unit.test_child.test_narrative_pipeline import _facts

from app.modules.child.context_resolver import ContextResolution, ResolverAgeSnapshot
from app.modules.child.guidance_facts import (
    CURRENT_GUIDANCE_FACTS_CONTRACT_VERSION,
    ChildGuidanceFacts,
    GuidanceInteractionScore,
    GuidanceProfileScore,
    _resolution_entries,
    build_guidance_facts,
)
from app.modules.child.narrative import build_child_section_inputs
from app.modules.child.quality import validate_guidance_facts


def _middle_facts(*, contract_version: str = "child-guidance-facts-v2") -> ChildGuidanceFacts:
    from uuid import uuid4

    from tests.unit.test_child.test_context_resolver import _answers, _scores

    from app.modules.child.context_resolver import resolve_context

    base = _current_facts()
    age = ResolverAgeSnapshot(base.age_snapshot_id, "3-6", date(2026, 10, 22), "child-age-mvp-1")
    scores: list[dict[str, Any]] = [
        {**item, "score": 53.0, "confidence": 0.7, "pattern": "moderate_tension"} for item in _scores()
    ]
    resolution = resolve_context(
        child_profile_id=base.child_id,
        generation_id=base.generation_id,
        questionnaire_session_id=uuid4(),
        age_snapshot=age,
        interaction_scores=scores,
        answers=_answers(),
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
                float(item["score"]),
                float(item["confidence"]),
                str(item["pattern"]),
                str(item["scoring_version"]),
                (f"child_interaction_scores:{item['id']}:{item['scoring_version']}",),
            )
            for item in scores
        ),
        profile_scores=tuple(
            GuidanceProfileScore(
                str(item["source_kind"]),
                str(item["dimension"]),
                float(item["score"]),
                float(item["confidence"]),
                str(item["scoring_version"]),
                tuple(item["evidence_refs"]),
            )
            for item in base.source_profiles
        ),
        contract_version=contract_version,
    )


@pytest.mark.asyncio
async def test_middle_topics_survive_validated_generation_with_distinct_reading_instruction() -> None:
    from app.modules.child.narrative import MockChildSegmentProvider, run_child_segment_generation

    facts = _middle_facts()
    inputs = {item.section_key: item for item in build_child_section_inputs(facts)}
    sections = (
        "how_to_use",
        "soothing_support",
        "boundaries_rules",
        "autonomy",
        "explanation_learning",
        "praise_recognition",
    )
    rows = [
        await run_child_segment_generation(
            provider=MockChildSegmentProvider(), section_input=inputs[key], guidance_facts=facts
        )
        for key in sections
    ]
    assert all(row.status == "ready" for row in rows)
    assert len({row.content for row in rows}) == len(sections)
    assert "читать" in (rows[0].content or "").lower()
    assert "general" not in (rows[0].content or "")
    assert "от 3 до 6 лет" in (rows[0].content or "")
    assert "не дают однозначного" in (rows[1].content or "")
    assert "спокойств" in (rows[1].content or "")
    assert "правил" in (rows[2].content or "")
    assert "самостоятельност" in (rows[3].content or "")
    assert "похвала" in (rows[5].content or "")
    assert rows[0].prompt_version == "child-section-prompt-v2"
    generic = "проверить небольшое изменение и наблюдать за результатом"
    for key in ("soothing_support", "boundaries_rules", "autonomy", "explanation_learning"):
        text = " ".join(fact.approved_text for fact in inputs[key].owned_facts)
        assert generic not in text  # A topic prefix cannot rescue the old generic action.
    assert "возвращается к спокойствию" in (rows[1].content or "")
    assert "формулировке правила" in (rows[2].content or "")
    assert "объёме помощи" in (rows[3].content or "")
    assert any(fact.family == "source_profiles" for fact in inputs["autonomy"].owned_facts)
    for key in ("soothing_support", "boundaries_rules", "explanation_learning"):
        assert any(fact.family == "source_profiles" for fact in inputs[key].owned_facts)


def _current_facts(
    *, parent_score: float = 57.0, parent_confidence: float = 0.7, contract_version: str = "child-guidance-facts-v2"
) -> ChildGuidanceFacts:
    legacy = _facts()
    action = next(item for item in legacy.recommended_actions if item["topic"] == "current_age")
    age_entry = {
        "id": action["id"].split(":", 1)[1],
        "topic": "current_age",
        "dimension": None,
        "confidence": 1.0,
        "source_refs": list(action["evidence_refs"]),
        "reason_code": action["reason_code"],
        "action_code": action["action_code"],
        "applicability": "3-6",
    }
    resolution = ContextResolution(
        "child-context-resolver-mvp-1", "a" * 64, (), (), (), _resolution_entries([age_entry]), (), (), ()
    )
    return build_guidance_facts(
        parent_profile_id=legacy.parent_profile_id,
        child_id=legacy.child_id,
        generation_id=legacy.generation_id,
        core_report_version=1,
        age_snapshot=ResolverAgeSnapshot(legacy.age_snapshot_id, "3-6", date(2026, 10, 22), "child-age-mvp-1"),
        resolution=resolution,
        interaction_scores=(),
        contract_version=contract_version,
        profile_scores=(
            *(
                GuidanceProfileScore(
                    "child_needs",
                    dimension,
                    52.0,
                    0.65,
                    "child-needs-mvp-1",
                    (f"child_need_scores:00000000-0000-4000-8000-{index:012d}:child-needs-mvp-1",),
                )
                for index, dimension in enumerate(
                    (
                        "predictability",
                        "verbal_explanation",
                        "physical_sensory_calm",
                        "exploration",
                        "personal_space",
                        "transition_time",
                        "variety",
                    ),
                    start=1,
                )
            ),
            GuidanceProfileScore(
                "child_needs",
                "reassurance",
                56.0,
                0.6,
                "child-needs-mvp-1",
                ("child_need_scores:44444444-4444-4444-8444-444444444444:child-needs-mvp-1",),
            ),
            GuidanceProfileScore(
                "child_needs",
                "autonomy",
                58.0,
                0.65,
                "child-needs-mvp-1",
                ("child_need_scores:33333333-3333-4333-8333-333333333333:child-needs-mvp-1",),
            ),
            GuidanceProfileScore(
                "parent_style",
                "structure",
                parent_score,
                parent_confidence,
                "parent-style-mvp-2",
                ("child_parent_style_scores:11111111-1111-4111-8111-111111111111:parent-style-mvp-2",),
            ),
            GuidanceProfileScore(
                "child_needs",
                "recognition",
                54.0,
                0.6,
                "child-needs-mvp-1",
                ("child_need_scores:22222222-2222-4222-8222-222222222222:child-needs-mvp-1",),
            ),
        ),
    )


@pytest.mark.asyncio
async def test_transition_observation_reaches_owned_adjustment_section() -> None:
    from app.modules.child.narrative import MockChildSegmentProvider, run_child_segment_generation

    facts = _middle_facts()
    transition = next(fact for fact in facts.recommended_actions if fact["topic"] == "transitions")
    inputs = {item.section_key: item for item in build_child_section_inputs(facts)}
    section = inputs["conscious_adjustments"]
    assert any(fact.family == "recommended_actions" for fact in section.owned_facts)
    assert any("лёгких и трудных переключений" in fact.approved_text for fact in section.owned_facts)
    row = await run_child_segment_generation(
        provider=MockChildSegmentProvider(), section_input=section, guidance_facts=facts
    )
    assert row.status == "ready"
    assert transition["id"] in row.evidence_refs
    assert "лёгких и трудных переключений" in (row.content or "")
    other_topic_ids = {fact["id"] for fact in facts.recommended_actions if fact["topic"] != "transitions"}
    assert not other_topic_ids.intersection(row.evidence_refs)
    from app.modules.child.safety import ChildSafetyViolation, NarrativeSectionCandidate, validate_child_narrative

    with pytest.raises(ChildSafetyViolation) as rejected:
        validate_child_narrative(
            NarrativeSectionCandidate(
                section_key=section.section_key,
                content="Взрослый может наблюдать реакцию на правило.",
                fact_refs=(*row.evidence_refs, next(iter(other_topic_ids))),
            ),
            guidance_facts=facts,
        )
    assert "section_fact_ownership" in rejected.value.categories


def test_current_facts_retain_middle_source_profiles_without_inventing_strengths() -> None:
    facts = _current_facts()
    validate_guidance_facts(facts)
    payload = facts.to_payload()
    assert {item["source_kind"] for item in payload["source_profiles"]} == {"parent_style", "child_needs"}
    assert not facts.strong_matches and not facts.friction_points
    assert "source_profiles" not in _facts().to_payload()
    inputs = {item.section_key: item for item in build_child_section_inputs(facts)}
    assert inputs["parent_style"].owned_facts
    assert inputs["child_interaction_needs"].owned_facts
    assert inputs["praise_recognition"].owned_facts
    assert inputs["praise_recognition"].owned_facts != inputs["how_to_use"].owned_facts
    style_text = inputs["parent_style"].owned_facts[0].approved_text
    praise_text = inputs["praise_recognition"].owned_facts[0].approved_text
    assert "свободной организации" in style_text and "распорядку и правилам" in style_text
    assert "усилий и вклада" in praise_text and "явной обратной связи" in praise_text
    assert "57" not in style_text and "0.7" not in style_text
    assert "54" not in praise_text and "0.6" not in praise_text


def test_v2_does_not_relabel_pair_strength_as_a_primary_parent_strength() -> None:
    from app.modules.child.context_resolver import ResolutionEntry

    legacy = _facts()
    raw = legacy.parent_strengths[0]
    strength = ResolutionEntry(
        id=raw["id"].split(":", 1)[1],
        topic=raw["topic"],
        dimension=raw["dimension"],
        confidence=raw["confidence"],
        source_refs=tuple(raw["evidence_refs"]),
        reason_code=raw["reason_code"],
        action_code=raw["action_code"],
    )
    age_action = next(item for item in legacy.recommended_actions if item["topic"] == "current_age")
    age_entry = ResolutionEntry(
        id=age_action["id"].split(":", 1)[1],
        topic="current_age",
        dimension=None,
        confidence=1.0,
        source_refs=tuple(age_action["evidence_refs"]),
        reason_code=age_action["reason_code"],
        action_code=age_action["action_code"],
        applicability="3-6",
    )
    current = build_guidance_facts(
        parent_profile_id=legacy.parent_profile_id,
        child_id=legacy.child_id,
        generation_id=legacy.generation_id,
        core_report_version=1,
        age_snapshot=ResolverAgeSnapshot(legacy.age_snapshot_id, "3-6", date(2026, 10, 22), "child-age-mvp-1"),
        resolution=ContextResolution(
            "child-context-resolver-mvp-1", "a" * 64, (strength,), (), (), (age_entry,), (), (), ()
        ),
        interaction_scores=(
            GuidanceInteractionScore(
                "boundary_fit", 78, 0.82, "natural_match", "child-interaction-mvp-1", tuple(raw["evidence_refs"])
            ),
        ),
        contract_version="child-guidance-facts-v2",
    )
    validate_guidance_facts(current)
    assert legacy.parent_strengths
    assert not current.parent_strengths
    inputs = {item.section_key: item for item in build_child_section_inputs(current)}
    assert inputs["natural_contact"].owned_facts
    assert "уже" not in inputs["natural_contact"].owned_facts[0].approved_text
    assert "Если в повседневном контакте" in inputs["boundaries_rules"].owned_facts[0].approved_text
    assert not inputs["parent_strengths"].owned_facts


def test_parent_resource_summary_is_not_a_copy_or_claim_of_observed_success() -> None:
    inputs = {item.section_key: item for item in build_child_section_inputs(_current_facts(parent_score=74))}
    style = inputs["parent_style"].owned_facts[0].approved_text
    resource = inputs["parent_strengths"].owned_facts[0].approved_text
    assert style != resource
    assert "не доказывает" in resource and "конкретному ребёнку" in resource


@pytest.mark.asyncio
async def test_assembly_separates_technical_completion_from_semantic_coverage() -> None:
    from app.modules.child.assembly import assemble_child_report_payload
    from app.modules.child.narrative import MockChildSegmentProvider, run_child_segment_generation

    facts = _middle_facts()
    assert len([item for item in facts.source_profiles if item["source_kind"] == "interaction"]) == 8
    rows = [
        await run_child_segment_generation(
            provider=MockChildSegmentProvider(), section_input=item, guidance_facts=facts
        )
        for item in build_child_section_inputs(facts)
    ]
    assembly = assemble_child_report_payload(guidance_facts=facts, segment_rows=rows)
    assert assembly["status"] == "ready"
    assert assembly["quality"]["status"] == "limited"
    assert assembly["quality"]["omitted_sections"] == assembly["omitted_sections"]
    assert "insufficient_section_evidence" in assembly["quality"]["reason_codes"]
    assert assembly["quality"]["repeated_sections"] == []


@pytest.mark.asyncio
async def test_legacy_assembly_stays_readable_but_repetition_is_not_product_ready() -> None:
    from app.modules.child.assembly import assemble_child_report_payload, assess_child_report_quality
    from app.modules.child.narrative import MockChildSegmentProvider, run_child_segment_generation

    facts = _facts()
    rows = [
        await run_child_segment_generation(
            provider=MockChildSegmentProvider(), section_input=item, guidance_facts=facts
        )
        for item in build_child_section_inputs(facts)
    ]
    assembly = assemble_child_report_payload(guidance_facts=facts, segment_rows=rows)
    assert assembly["prompt_version"] == "child-section-prompt-v1"
    assert "quality" not in assembly  # Immutable v1 assembly hashes/semantics stay unchanged.
    legacy_quality = assess_child_report_quality(
        sections=assembly["sections"],
        omitted_sections=assembly["omitted_sections"],
        failed_sections=[],
        missing_sections=[],
    )
    assert legacy_quality["status"] == "limited"
    assert "repeated_section_content" in legacy_quality["reason_codes"]
    assert {"how_to_use", "child_interaction_needs"} <= set(legacy_quality["repeated_sections"])
    quality = assess_child_report_quality(
        sections=[{"section_key": "autonomy", "body": "Supported distinct body."}],
        omitted_sections=[],
        failed_sections=[],
        missing_sections=[],
    )
    assert quality == {"status": "ready", "reason_codes": [], "omitted_sections": [], "repeated_sections": []}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "stored_version", [None, "child-guidance-facts-v1", "child-guidance-facts-v2", "child-guidance-facts-v3"]
)
async def test_writer_uses_authoritative_profiles_for_new_contract_but_rebuilds_legacy_semantics(
    monkeypatch: pytest.MonkeyPatch,
    stored_version: str | None,
) -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock
    from uuid import UUID, uuid4

    from sqlalchemy.ext.asyncio import AsyncSession
    from tests.unit.test_child.test_context_resolver import _scores

    from app.modules.child.guidance_facts import ChildGuidanceFactsRepository
    from app.modules.child.questionnaire_persistence import ChildContextResolutionRepository
    from app.modules.child.repository import ChildRepository

    base = _current_facts()
    action = next(item for item in base.recommended_actions if item["topic"] == "current_age")
    resolution = SimpleNamespace(
        age_snapshot_id=base.age_snapshot_id,
        resolver_version="child-context-resolver-mvp-1",
        input_hash="a" * 64,
        natural_strengths=[],
        potential_friction=[],
        compensation_areas=[],
        confirmations=[],
        contradictions=[],
        unresolved_ambiguities=[],
        age_relevant_guidance=[
            {
                "id": action["id"].split(":", 1)[1],
                "topic": "current_age",
                "dimension": None,
                "confidence": 1.0,
                "source_refs": list(action["evidence_refs"]),
                "reason_code": action["reason_code"],
                "action_code": action["action_code"],
                "applicability": "3-6",
            }
        ],
    )
    age = SimpleNamespace(
        id=base.age_snapshot_id, age_stage="3-6", as_of_date=date(2026, 10, 22), age_rules_version="child-age-mvp-1"
    )
    scores = tuple(SimpleNamespace(**item) for item in _scores())
    session = AsyncMock(spec=AsyncSession)
    session.scalar.side_effect = [SimpleNamespace(parent_profile_id=base.parent_profile_id), age, None]
    session.scalars.return_value = MagicMock()
    session.scalars.return_value.all.return_value = [stored_version] if stored_version else []
    monkeypatch.setattr(ChildContextResolutionRepository, "load", AsyncMock(return_value=resolution))
    monkeypatch.setattr(
        ChildRepository, "load_interaction_profile", AsyncMock(return_value=SimpleNamespace(scores=scores))
    )
    loaders = []
    for kind, method in (("parent_style", "load_parent_style_profile"), ("child_needs", "load_child_need_profile")):
        rows = [
            SimpleNamespace(
                id=UUID(item["evidence_refs"][0].split(":")[1]),
                dimension=item["dimension"],
                score=item["score"],
                confidence=item["confidence"],
                scoring_version=item["scoring_version"],
            )
            for item in base.source_profiles
            if item["source_kind"] == kind
        ]
        loader = AsyncMock(return_value=SimpleNamespace(scores=rows))
        loaders.append(loader)
        monkeypatch.setattr(ChildRepository, method, loader)
    result = await ChildGuidanceFactsRepository(session).create_or_load(
        owner_user_id=uuid4(),
        child_profile_id=base.child_id,
        generation_id=base.generation_id,
        core_report_version=1,
    )
    expected = stored_version or CURRENT_GUIDANCE_FACTS_CONTRACT_VERSION
    assert result.artifact.contract_version == expected
    source_profiles_expected = stored_version != "child-guidance-facts-v1"
    assert ("source_profiles" in result.artifact.payload) is source_profiles_expected
    for loader in loaders:
        assert loader.await_count == int(source_profiles_expected)


@pytest.mark.parametrize("contract_version", ["child-guidance-facts-v2", "child-guidance-facts-v3"])
@pytest.mark.parametrize("mutation", ["source_kind", "score", "dimension", "policy_version", "raw_answer"])
def test_current_facts_reject_semantic_forgery_even_with_recomputed_hash(mutation: str, contract_version: str) -> None:
    from app.modules.child.quality import GuidanceFactsQualityError, _guidance_payload_hash

    payload = _current_facts(contract_version=contract_version).to_payload()
    fact = payload["source_profiles"][0]
    if mutation == "policy_version":
        metadata = next(
            item for item in payload["evidence_registry"].values() if item["source_type"] == "guidance_contract"
        )
        metadata["contract_version"] = "child-guidance-facts-v1"
    elif mutation == "raw_answer":
        fact["answer"] = "private observation"
    elif mutation == "source_kind":
        fact["source_kind"] = "parent_style"
        fact["dimension"] = "structure"
        fact["scoring_version"] = "parent-style-mvp-2"
        fact["id"] = "profile:parent_style:structure"
        payload["evidence_registry"][fact["evidence_refs"][0]].update(
            {key: fact[key] for key in ("source_kind", "dimension", "scoring_version")}
        )
    elif mutation == "score":
        fact["score"] = 99.0
    else:
        fact["dimension"] = "reassurance"
        fact["id"] = "profile:child_needs:reassurance"
    old_key = next(
        key for key, item in payload["evidence_registry"].items() if item["source_type"] == "guidance_contract"
    )
    metadata = payload["evidence_registry"].pop(old_key)
    digest = _guidance_payload_hash(payload)
    assert digest is not None
    metadata["input_hash"] = digest
    payload["evidence_registry"][f"guidance_contract:{digest}"] = metadata
    with pytest.raises(GuidanceFactsQualityError):
        validate_guidance_facts(payload)


@pytest.mark.asyncio
@pytest.mark.parametrize("contract_version", ["child-guidance-facts-v2", "child-guidance-facts-v3"])
async def test_current_sections_reject_cross_source_citations_and_invented_prose(contract_version: str) -> None:
    from tests.unit.test_child.test_narrative_pipeline import _output

    from app.modules.child.narrative import ChildNarrativeValidationError, validate_segment_output
    from app.modules.child.safety import ChildSafetyViolation, NarrativeSectionCandidate, validate_child_narrative

    facts = _current_facts(contract_version=contract_version)
    inputs = {item.section_key: item for item in build_child_section_inputs(facts)}
    parent_id = next(item["id"] for item in facts.source_profiles if item["source_kind"] == "parent_style")
    with pytest.raises(ChildSafetyViolation) as rejected:
        validate_child_narrative(
            NarrativeSectionCandidate(
                section_key="praise_recognition", content="Взрослый может наблюдать.", fact_refs=(parent_id,)
            ),
            guidance_facts=facts,
        )
    assert "section_fact_ownership" in rejected.value.categories
    canonical = inputs["praise_recognition"]
    output = _output(canonical)
    with pytest.raises(ChildNarrativeValidationError, match="fully covered"):
        validate_segment_output(
            output=output.model_copy(update={"body": output.body + " Ребёнок талантлив от рождения."}),
            section_input=canonical,
            guidance_facts=facts,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_kind", {}),
        ("dimension", []),
        ("score", "NaN"),
        ("confidence", None),
        ("evidence_refs", [["nested"]]),
        ("registry_contract_version", []),
    ],
)
def test_current_source_validation_is_total_over_hostile_shapes(field: str, value: Any) -> None:
    from app.modules.child.quality import GuidanceFactsQualityError

    payload = _current_facts().to_payload()
    if field == "registry_contract_version":
        metadata = next(
            item for item in payload["evidence_registry"].values() if item["source_type"] == "guidance_contract"
        )
        metadata["contract_version"] = value
    else:
        payload["source_profiles"][0][field] = value
    with pytest.raises(GuidanceFactsQualityError):
        validate_guidance_facts(payload)


def test_multi_family_section_inputs_have_identical_hashes_across_worker_processes() -> None:
    import os
    import subprocess
    import sys
    from pathlib import Path

    script = (
        "import hashlib,json; "
        "from tests.unit.test_child.test_content_v2 import _middle_facts; "
        "from app.modules.child.narrative import build_child_section_inputs; "
        "print(hashlib.sha256(json.dumps([item.model_dump(mode='json') "
        "for item in build_child_section_inputs(_middle_facts())],sort_keys=True).encode()).hexdigest())"
    )
    hashes = [
        subprocess.run(  # noqa: S603 — fixed interpreter/script; no caller-controlled command.
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[3],
            env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        for seed in ("0", "1", "42", "99")
    ]
    assert len(set(hashes)) == 1
