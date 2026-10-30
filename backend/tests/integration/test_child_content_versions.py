"""Versioned repair uses new immutable artifacts; old payloads remain readable."""

from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from typing import Any, cast

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.dependencies import get_current_user
from app.main import app
from app.modules.child import models
from app.modules.child.age_resolver import AgeStage
from app.modules.child.context_resolver import ContextResolution, ResolverAgeSnapshot
from app.modules.child.guidance_facts import (
    ChildGuidanceFactsRepository,
    GuidanceInteractionScore,
    GuidanceProfileScore,
    _resolution_entries,
    build_guidance_facts,
)
from app.modules.child.presentation import build_child_report_presentation
from app.modules.child.questionnaire_persistence import ChildContextResolutionRepository
from app.modules.child.repository import ChildRepository
from app.modules.child.service import (
    accept_narrative_retry_generation,
    run_claimed_full_generation,
    run_claimed_narrative_retry,
)
from tests.integration.test_child_generation_lifecycle import (
    NOW,
    CountingProvider,
    _grant_direct_child_access,
    _seed_claimable_full_pipeline,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.usefixtures("_setup_database")]


@pytest.mark.parametrize(
    "legacy_contract", ["child-guidance-facts-v1", "child-guidance-facts-v2", "child-guidance-facts-v3"]
)
async def test_legacy_read_and_new_full_report_repair_preserve_old_hashes_and_public_pdf(
    db_session: AsyncSession,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    legacy_contract: str,
) -> None:
    seed, legacy_generation = await _seed_claimable_full_pipeline(db_session, idempotency_key="legacy-content")
    context_row = (
        await ChildContextResolutionRepository(db_session).create_or_load(
            owner_user_id=seed.owner_id,
            child_profile_id=seed.child_id,
            generation_id=legacy_generation.generation_id,
            questionnaire_session_id=seed.questionnaire_id,
        )
    ).resolution
    child = await db_session.get(models.ChildProfile, seed.child_id)
    age = await db_session.get(models.ChildAgeSnapshot, context_row.age_snapshot_id)
    assert child is not None and age is not None
    interaction = await ChildRepository(db_session).load_interaction_profile(
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        generation_id=legacy_generation.generation_id,
    )
    resolution = ContextResolution(
        resolver_version=context_row.resolver_version,
        input_hash=context_row.input_hash,
        **{
            key: _resolution_entries(getattr(context_row, key))
            for key in (
                "natural_strengths",
                "potential_friction",
                "compensation_areas",
                "age_relevant_guidance",
                "confirmations",
                "contradictions",
                "unresolved_ambiguities",
            )
        },
    )
    profile_scores: list[GuidanceProfileScore] = []
    if legacy_contract in {"child-guidance-facts-v2", "child-guidance-facts-v3"}:
        for kind, table, loader in (
            ("parent_style", "child_parent_style_scores", ChildRepository(db_session).load_parent_style_profile),
            ("child_needs", "child_need_scores", ChildRepository(db_session).load_child_need_profile),
        ):
            profile = await loader(
                owner_user_id=seed.owner_id,
                child_profile_id=seed.child_id,
                generation_id=legacy_generation.generation_id,
            )
            profile_scores.extend(
                GuidanceProfileScore(
                    kind,
                    row.dimension,
                    float(row.score),
                    float(row.confidence),
                    row.scoring_version,
                    (f"{table}:{row.id}:{row.scoring_version}",),
                )
                for row in profile.scores
            )
    domain = build_guidance_facts(
        parent_profile_id=child.parent_profile_id,
        child_id=seed.child_id,
        generation_id=legacy_generation.generation_id,
        core_report_version=1,
        age_snapshot=ResolverAgeSnapshot(age.id, cast(AgeStage, age.age_stage), age.as_of_date, age.age_rules_version),
        resolution=resolution,
        contract_version=legacy_contract,
        profile_scores=tuple(profile_scores),
        interaction_scores=tuple(
            GuidanceInteractionScore(
                row.dimension,
                float(row.score),
                float(row.confidence),
                row.pattern,
                row.scoring_version,
                (f"child_interaction_scores:{row.id}:{row.scoring_version}",),
            )
            for row in interaction.scores
        ),
    )
    payload = domain.to_payload()
    registry = payload.pop("evidence_registry")
    legacy_facts = models.ChildGuidanceFacts(
        child_profile_id=seed.child_id,
        generation_id=legacy_generation.generation_id,
        age_snapshot_id=age.id,
        contract_version=domain.contract_version,
        core_report_version=1,
        payload=payload,
        evidence_registry=registry,
    )
    db_session.add(legacy_facts)
    await db_session.commit()
    repository = ChildRepository(db_session)
    claim = await repository.claim_generation(
        generation_id=legacy_generation.generation_id, task_id="legacy", now=NOW, lease_duration=timedelta(minutes=5)
    )
    assert claim is not None
    await db_session.commit()
    with monkeypatch.context() as historical:
        historical.setattr(
            "app.modules.child.service.CURRENT_CHILD_PROMPT_VERSION", "child-section-prompt-v3", raising=False
        )
        legacy_result = await run_claimed_full_generation(db_session, claim=claim, provider=CountingProvider(), now=NOW)
    assert legacy_result.report_id is not None
    legacy_report = await db_session.get(models.ChildReport, legacy_result.report_id)
    expected_prompt = "child-section-prompt-" + legacy_contract.rsplit("-", 1)[1]
    expected_assembly = "child_report_narrative_" + legacy_contract.rsplit("-", 1)[1]
    assert legacy_report is not None and legacy_report.prompt_version == expected_prompt
    old_segments = {
        row.id: deepcopy(row.diagnostics)
        for row in (
            await db_session.scalars(
                select(models.ChildSegmentGeneration).where(
                    models.ChildSegmentGeneration.generation_id == legacy_generation.generation_id
                )
            )
        ).all()
    }
    old_payload = deepcopy(legacy_report.report_payload)
    old_registry = deepcopy(registry)
    legacy_retry = await accept_narrative_retry_generation(
        db_session,
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        source_report_id=legacy_report.id,
        idempotency_key="legacy-narrative-only",
        scope="narrative_all",
        now=NOW,
        dispatcher=lambda *, generation_id: f"child-generation-{generation_id}",
    )
    retry_claim = await repository.claim_generation(
        generation_id=legacy_retry.generation_id,
        task_id="legacy-retry",
        now=NOW + timedelta(minutes=1),
        lease_duration=timedelta(minutes=5),
    )
    assert retry_claim is not None
    await db_session.commit()
    retry_result = await run_claimed_narrative_retry(
        db_session,
        claim=retry_claim,
        provider=CountingProvider(),
        now=NOW + timedelta(minutes=1),
    )
    assert retry_result.status == "ready"
    retry_assembly = await db_session.scalar(
        select(models.ChildReportAssembly).where(
            models.ChildReportAssembly.generation_id == legacy_retry.generation_id,
        )
    )
    assert retry_assembly is not None
    assert retry_assembly.payload["prompt_version"] == expected_prompt
    assert retry_assembly.contract_version == expected_assembly
    assert ("quality" in retry_assembly.payload) is not legacy_contract.endswith("v1")
    old_retry_payload = deepcopy(retry_assembly.payload)
    old_presentation = await build_child_report_presentation(
        db_session, owner_user_id=seed.owner_id, report_id=legacy_report.id
    )
    assert old_presentation["quality"]["status"] == "limited"

    # The same aggregate also keeps a v2 publication while v1 remains present.
    # Simulate only the historical writer's default selection; every repository,
    # provider boundary, persistence step, and retry/reader below is real.
    v2_report: models.ChildReport | None = None
    v2_snapshot: dict[str, Any] | None = None
    if legacy_contract == "child-guidance-facts-v1":
        v2_generation = await repository.create_generation_idempotently(
            owner_user_id=seed.owner_id,
            child_profile_id=seed.child_id,
            parent_chart_id=seed.parent_chart_id,
            child_chart_version_id=seed.child_chart_id,
            questionnaire_session_id=seed.questionnaire_id,
            operation="full_report",
            idempotency_key="historical-v2-full-report",
        )
        await db_session.commit()
        v2_claim = await repository.claim_generation(
            generation_id=v2_generation.generation.generation_id,
            task_id="historical-v2",
            now=NOW,
            lease_duration=timedelta(minutes=5),
        )
        assert v2_claim is not None
        await db_session.commit()
        with monkeypatch.context() as historical_default:
            historical_default.setattr(
                "app.modules.child.guidance_facts.CURRENT_GUIDANCE_FACTS_CONTRACT_VERSION", "child-guidance-facts-v2"
            )
            v2_result = await run_claimed_full_generation(
                db_session, claim=v2_claim, provider=CountingProvider(), now=NOW
            )
        assert v2_result.report_id is not None
        v2_report = await db_session.get(models.ChildReport, v2_result.report_id)
        assert v2_report is not None and v2_report.prompt_version == "child-section-prompt-v2"
        v2_snapshot = deepcopy(v2_report.report_payload)
        await db_session.commit()

    # Explicit user-authorized full regeneration gets a new generation and narrative v4;
    # unchanged Guidance Facts v3 are reused without reinterpreting older narrative retries.
    repair = await repository.create_generation_idempotently(
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        parent_chart_id=seed.parent_chart_id,
        child_chart_version_id=seed.child_chart_id,
        questionnaire_session_id=seed.questionnaire_id,
        operation="full_report",
        idempotency_key="explicit-content-repair",
    )
    await db_session.commit()
    repair_claim = await repository.claim_generation(
        generation_id=repair.generation.generation_id, task_id="repair", now=NOW, lease_duration=timedelta(minutes=5)
    )
    assert repair_claim is not None
    await db_session.commit()
    repaired = await run_claimed_full_generation(db_session, claim=repair_claim, provider=CountingProvider(), now=NOW)
    assert repaired.report_id is not None and repaired.report_id != legacy_report.id
    repaired_report = await db_session.get(models.ChildReport, repaired.report_id)
    assert repaired_report is not None and repaired_report.prompt_version == "child-section-prompt-v4"
    repaired_assembly = await db_session.scalar(
        select(models.ChildReportAssembly).where(
            models.ChildReportAssembly.generation_id == repair.generation.generation_id
        )
    )
    assert repaired_assembly is not None and repaired_assembly.contract_version == "child_report_narrative_v4"
    await db_session.commit()
    assert isinstance(db_session.bind, AsyncEngine)
    sessions = async_sessionmaker(db_session.bind, expire_on_commit=False)
    async with sessions() as reader:
        preserved = await reader.get(models.ChildReport, legacy_report.id)
        if v2_report is not None:
            preserved_v2 = await reader.get(models.ChildReport, v2_report.id)
            assert preserved_v2 is not None and preserved_v2.report_payload == v2_snapshot
            assert set(
                (
                    await reader.scalars(
                        select(models.ChildGuidanceFacts.contract_version).where(
                            models.ChildGuidanceFacts.child_profile_id == seed.child_id,
                        )
                    )
                ).all()
            ) == {"child-guidance-facts-v1", "child-guidance-facts-v2", "child-guidance-facts-v3"}
            repaired_row = await reader.get(models.ChildReport, repaired.report_id)
            assert repaired_row is not None and repaired_row.version == 3
        assert preserved is not None and preserved.report_payload == old_payload
        for segment_id, diagnostics in old_segments.items():
            segment = await reader.get(models.ChildSegmentGeneration, segment_id)
            assert segment is not None and segment.diagnostics == diagnostics
        retry_preserved = await reader.get(models.ChildReportAssembly, retry_assembly.id)
        assert retry_preserved is not None and retry_preserved.payload == old_retry_payload
        preserved_facts = await reader.get(models.ChildGuidanceFacts, legacy_facts.id)
        assert preserved_facts is not None and preserved_facts.evidence_registry == old_registry
        assert (
            await ChildGuidanceFactsRepository(reader).load_domain_facts(
                owner_user_id=seed.owner_id,
                child_profile_id=seed.child_id,
                generation_id=legacy_generation.generation_id,
                core_report_version=1,
            )
        ).input_hash == domain.input_hash
        assert (
            await build_child_report_presentation(reader, owner_user_id=seed.owner_id, report_id=legacy_report.id)
            == old_presentation
        )
        current = await reader.scalar(
            select(models.ChildGuidanceFacts).where(
                models.ChildGuidanceFacts.generation_id == repair.generation.generation_id,
            )
        )
        assert current is not None and current.contract_version == "child-guidance-facts-v3"
        assert len(current.payload["source_profiles"]) == 26
        transition_ids = {
            fact["id"] for fact in current.payload["recommended_actions"] if fact["topic"] == "transitions"
        }
        assert transition_ids
        adjustments = await reader.scalar(
            select(models.ChildSegmentGeneration).where(
                models.ChildSegmentGeneration.generation_id == repair.generation.generation_id,
                models.ChildSegmentGeneration.section_key == "conscious_adjustments",
            )
        )
        assert adjustments is not None and adjustments.status == "ready"
        assert transition_ids <= set(adjustments.evidence_refs)
        assert (
            next(
                item["input_hash"]
                for item in current.evidence_registry.values()
                if item["source_type"] == "guidance_contract"
            )
            != domain.input_hash
        )

    await _grant_direct_child_access(db_session, user_id=seed.owner_id)
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", True)
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    response = await client.get(f"/api/v1/child/reports/{repaired.report_id}")
    assert response.status_code == 200, response.text
    public: dict[str, Any] = response.json()["presentation"]
    assert public["quality"]["status"] in {"ready", "limited"}
    assert "repeated_section_content" not in public["quality"]["reason_codes"]
    all_prose = " ".join(section["body"] or "" for section in public["sections"])
    assert all_prose.count("Это не оценка способностей и не фиксированная черта ребёнка") == 1
    assert all_prose.count("Расчёт находится между полюсами шкалы") == 0
    by_key = {section["key"]: section for section in public["sections"]}
    assert "стиля взрослого" in by_key["parent_style"]["body"]
    assert "возможных потребностей" in by_key["child_interaction_needs"]["body"]
    assert by_key["how_to_use"]["body"] != by_key["child_interaction_needs"]["body"]
    pdf = await client.get(f"/api/v1/child/reports/{repaired.report_id}/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-"), pdf.text[:200]
    import re
    from io import BytesIO

    from pypdf import PdfReader

    # Page counters are layout, not narrative; remove only standalone footer
    # lines before testing complete prose parity across a page boundary.
    pdf_text = " ".join(
        re.sub(r"(?m)^\d+\s*$", "", page.extract_text()) for page in PdfReader(BytesIO(pdf.content)).pages
    )
    normalized_pdf = " ".join(pdf_text.replace("\u00ad", "").split())
    for section in public["sections"]:
        if section["body"]:
            assert " ".join(section["body"].split()) in normalized_pdf
        elif section["status"] == "not_applicable":
            assert "Для отдельного пояснения пока недостаточно устойчивых оснований." in normalized_pdf
