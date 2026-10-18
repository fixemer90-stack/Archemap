from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.audit import AuditLog
from app.modules.astrotype_v2.models import NatalChart
from app.modules.child import models
from app.modules.child.repository import ChildLineageMismatchError, ChildRepository
from app.modules.profiles.models import PersonProfile
from app.modules.users.models import User

pytestmark = pytest.mark.usefixtures("_setup_database")


async def _seed_owner_roots(
    db_session: AsyncSession,
) -> tuple[User, PersonProfile, NatalChart, User, PersonProfile, NatalChart]:
    owner = User(
        email=f"child-owner-{uuid4()}@example.com",
        name="Owner",
        hashed_password="test-only-hash",  # noqa: S106
        is_active=True,
        is_verified=True,
    )
    foreign_owner = User(
        email=f"child-foreign-{uuid4()}@example.com",
        name="Foreign",
        hashed_password="test-only-hash",  # noqa: S106
        is_active=True,
        is_verified=True,
    )
    db_session.add_all([owner, foreign_owner])
    await db_session.flush()
    parent_profile = PersonProfile(
        user_id=owner.id,
        name="Owner",
        birth_date=date(1990, 1, 1),
        birth_time=None,
        birth_time_accuracy="unknown",
        birth_place="Москва",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
    )
    foreign_profile = PersonProfile(
        user_id=foreign_owner.id,
        name="Foreign",
        birth_date=date(1991, 2, 2),
        birth_time=None,
        birth_time_accuracy="unknown",
        birth_place="Казань",
        latitude=55.7963,
        longitude=49.1088,
        timezone="Europe/Moscow",
    )
    db_session.add_all([parent_profile, foreign_profile])
    await db_session.flush()
    parent_chart = NatalChart(
        user_id=owner.id,
        profile_id=parent_profile.id,
        engine_version="test-v1",
        input_hash="p" * 64,
        birth_datetime_utc=datetime(1990, 1, 1, tzinfo=UTC),
        timezone="Europe/Moscow",
        latitude=55.7558,
        longitude=37.6173,
        house_system="P",
        calculation_payload={},
    )
    foreign_chart = NatalChart(
        user_id=foreign_owner.id,
        profile_id=foreign_profile.id,
        engine_version="test-v1",
        input_hash="f" * 64,
        birth_datetime_utc=datetime(1991, 2, 2, tzinfo=UTC),
        timezone="Europe/Moscow",
        latitude=55.7963,
        longitude=49.1088,
        house_system="P",
        calculation_payload={},
    )
    db_session.add_all([parent_chart, foreign_chart])
    await db_session.commit()
    return owner, parent_profile, parent_chart, foreign_owner, foreign_profile, foreign_chart


async def _create_child(
    db_session: AsyncSession,
    *,
    owner: User,
    parent_profile: PersonProfile,
    key: str,
    name: str,
) -> models.ChildProfile:
    result = await ChildRepository(db_session).create_child_idempotently(
        owner_user_id=owner.id,
        parent_profile_id=parent_profile.id,
        display_name=name,
        relationship_type="child",
        child_gender=None,
        birth_date=date(2021, 5, 12),
        birth_time=None,
        birth_time_confidence="unknown",
        birth_place="Москва",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
        caregiver_context={},
        birth_data_hash=key[0] * 64,
        idempotency_key=key,
    )
    await db_session.commit()
    return result.child


@pytest.mark.asyncio
async def test_database_rejects_cross_child_and_cross_generation_lineage(db_session: AsyncSession) -> None:
    owner, parent_profile, parent_chart, _, foreign_profile, foreign_chart = await _seed_owner_roots(db_session)
    with pytest.raises(ChildLineageMismatchError):
        await ChildRepository(db_session).create_child_idempotently(
            owner_user_id=owner.id,
            parent_profile_id=foreign_profile.id,
            display_name="Foreign lineage",
            relationship_type="child",
            child_gender=None,
            birth_date=date(2021, 5, 12),
            birth_time=None,
            birth_time_confidence="unknown",
            birth_place="Казань",
            latitude=55.7963,
            longitude=49.1088,
            timezone="Europe/Moscow",
            caregiver_context={},
            birth_data_hash="f" * 64,
            idempotency_key="foreign-profile",
        )
    first = await _create_child(db_session, owner=owner, parent_profile=parent_profile, key="a-child", name="A")
    second = await _create_child(db_session, owner=owner, parent_profile=parent_profile, key="b-child", name="B")

    first_chart = models.ChildChartVersion(
        child_profile_id=first.id,
        version=1,
        engine_version="child-chart-v1",
        input_hash="1" * 64,
        birth_time_confidence="unknown",
        allowed_fact_families=["planets"],
        excluded_fact_families=["houses"],
        uncertainty_reason="unknown_time",
        calculation_payload={},
    )
    second_chart = models.ChildChartVersion(
        child_profile_id=second.id,
        version=1,
        engine_version="child-chart-v1",
        input_hash="2" * 64,
        birth_time_confidence="unknown",
        allowed_fact_families=["planets"],
        excluded_fact_families=["houses"],
        uncertainty_reason="unknown_time",
        calculation_payload={},
    )
    db_session.add_all([first_chart, second_chart])
    await db_session.flush()
    with pytest.raises(ChildLineageMismatchError):
        await ChildRepository(db_session).create_generation_idempotently(
            owner_user_id=owner.id,
            child_profile_id=first.id,
            parent_chart_id=foreign_chart.id,
            child_chart_version_id=first_chart.id,
            operation="generate",
            idempotency_key="foreign-parent-chart",
        )
    first_id = first.id
    second_id = second.id
    first_generation_id = uuid4()
    second_generation_id = uuid4()
    db_session.add_all(
        [
            models.ChildGeneration(
                child_profile_id=first_id,
                owner_user_id=owner.id,
                parent_chart_id=parent_chart.id,
                child_chart_version_id=first_chart.id,
                generation_id=first_generation_id,
                operation="generate",
                idempotency_key="gen-a",
                status="queued",
                diagnostics={},
            ),
            models.ChildGeneration(
                child_profile_id=second_id,
                owner_user_id=owner.id,
                parent_chart_id=parent_chart.id,
                child_chart_version_id=second_chart.id,
                generation_id=second_generation_id,
                operation="generate",
                idempotency_key="gen-b",
                status="queued",
                diagnostics={},
            ),
        ]
    )
    await db_session.commit()

    db_session.add(
        models.ChildInteractionScore(
            child_profile_id=first_id,
            parent_chart_id=parent_chart.id,
            child_chart_version_id=second_chart.id,
            generation_id=second_generation_id,
            dimension="boundary_fit",
            score=50,
            confidence=0.5,
            pattern="balanced",
            scoring_version="score-v1",
            evidence_refs=["evidence:1"],
            breakdown={},
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    age = models.ChildAgeSnapshot(
        child_profile_id=first_id,
        as_of_date=date(2026, 10, 14),
        age_years=5,
        age_months=5,
        age_days=2,
        age_stage="3-6",
        age_rules_version="age-v1",
        input_hash="3" * 64,
    )
    db_session.add(age)
    await db_session.commit()
    db_session.add(
        models.ChildQuestionnaireSession(
            child_profile_id=second_id,
            age_snapshot_id=age.id,
            status="draft",
            questionnaire_version="q-v1",
            context_version="c-v1",
            consent_version="consent-v1",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_generation_questionnaire_report_and_age_guidance_are_concurrently_idempotent(
    db_session: AsyncSession,
) -> None:
    owner, parent_profile, parent_chart, _, _, _ = await _seed_owner_roots(db_session)
    child = await _create_child(db_session, owner=owner, parent_profile=parent_profile, key="i-child", name="I")
    chart = models.ChildChartVersion(
        child_profile_id=child.id,
        version=1,
        engine_version="child-chart-v1",
        input_hash="4" * 64,
        birth_time_confidence="unknown",
        allowed_fact_families=["planets"],
        excluded_fact_families=["houses"],
        uncertainty_reason="unknown_time",
        calculation_payload={},
    )
    age = models.ChildAgeSnapshot(
        child_profile_id=child.id,
        as_of_date=date(2026, 10, 14),
        age_years=5,
        age_months=5,
        age_days=2,
        age_stage="3-6",
        age_rules_version="age-v1",
        input_hash="5" * 64,
    )
    db_session.add_all([chart, age])
    await db_session.flush()
    questionnaire = models.ChildQuestionnaireSession(
        child_profile_id=child.id,
        age_snapshot_id=age.id,
        status="draft",
        questionnaire_version="q-v1",
        context_version="c-v1",
        consent_version="consent-v1",
    )
    db_session.add(questionnaire)
    await db_session.commit()

    assert isinstance(db_session.bind, AsyncEngine)
    sessions = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)

    async def create_generation() -> tuple[bool, models.ChildGeneration]:
        async with sessions() as session:
            result = await ChildRepository(session).create_generation_idempotently(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                parent_chart_id=parent_chart.id,
                child_chart_version_id=chart.id,
                operation="generate",
                idempotency_key="generation-key",
            )
            await session.commit()
            return result.created, result.generation

    first_generation, second_generation = await asyncio.gather(create_generation(), create_generation())
    assert sorted([first_generation[0], second_generation[0]]) == [False, True]
    assert first_generation[1].generation_id == second_generation[1].generation_id
    generation = first_generation[1]

    async def complete_questionnaire() -> bool:
        async with sessions() as session:
            result = await ChildRepository(session).complete_questionnaire_idempotently(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                questionnaire_session_id=questionnaire.id,
                completion_idempotency_key="completion-key",
                answers_hash="6" * 64,
                completed_at=datetime.now(UTC),
            )
            await session.commit()
            return result.completed_now

    completion_results = await asyncio.gather(complete_questionnaire(), complete_questionnaire())
    assert sorted(completion_results) == [False, True]

    async def create_report() -> tuple[bool, models.ChildReport]:
        async with sessions() as session:
            result = await ChildRepository(session).create_report_idempotently(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                generation_id=generation.generation_id,
                parent_chart_id=parent_chart.id,
                child_chart_version_id=chart.id,
                idempotency_key="report-key",
                version=1,
                status="deterministic_ready",
                scoring_version="score-v1",
                reference_version="reference-v1",
                questionnaire_version="q-v1",
                prompt_version="prompt-v1",
                report_payload={"summary": "persisted"},
                presentation_manifest={"sections": ["summary"]},
            )
            await session.commit()
            return result.created, result.report

    first_report, second_report = await asyncio.gather(create_report(), create_report())
    assert sorted([first_report[0], second_report[0]]) == [False, True]
    assert first_report[1].id == second_report[1].id
    report = first_report[1]

    async def create_guidance() -> tuple[bool, models.ChildReportAgeGuidance]:
        async with sessions() as session:
            result = await ChildRepository(session).create_age_guidance_idempotently(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                report_id=report.id,
                age_snapshot_id=age.id,
                version=1,
                idempotency_key="age-guidance-key",
                status="age_update_ready",
                rules_version="age-guidance-v1",
                payload={"actions": ["pause"]},
            )
            await session.commit()
            return result.created, result.guidance

    first_guidance, second_guidance = await asyncio.gather(create_guidance(), create_guidance())
    assert sorted([first_guidance[0], second_guidance[0]]) == [False, True]
    assert first_guidance[1].id == second_guidance[1].id


async def _seed_complete_graph(
    db_session: AsyncSession,
) -> tuple[User, PersonProfile, NatalChart, models.ChildProfile, models.ChildProfile, models.ChildReport]:
    owner, parent_profile, parent_chart, _, _, _ = await _seed_owner_roots(db_session)
    child = await _create_child(db_session, owner=owner, parent_profile=parent_profile, key="g-child", name="Graph")
    sibling = await _create_child(db_session, owner=owner, parent_profile=parent_profile, key="s-child", name="Sibling")
    chart = models.ChildChartVersion(
        child_profile_id=child.id,
        version=1,
        engine_version="child-chart-v1",
        input_hash="7" * 64,
        birth_time_confidence="unknown",
        allowed_fact_families=["planets"],
        excluded_fact_families=["houses"],
        uncertainty_reason="unknown_time",
        calculation_payload={"planets": ["sun"]},
    )
    age = models.ChildAgeSnapshot(
        child_profile_id=child.id,
        as_of_date=date(2026, 10, 14),
        age_years=5,
        age_months=5,
        age_days=2,
        age_stage="3-6",
        age_rules_version="age-v1",
        input_hash="8" * 64,
    )
    db_session.add_all([chart, age])
    await db_session.flush()
    questionnaire = models.ChildQuestionnaireSession(
        child_profile_id=child.id,
        age_snapshot_id=age.id,
        status="completed",
        questionnaire_version="q-v1",
        context_version="context-v1",
        consent_version="consent-v1",
        completion_idempotency_key="completed-key",
        answers_hash="9" * 64,
        completed_at=datetime.now(UTC),
    )
    generation_id = uuid4()
    generation = models.ChildGeneration(
        child_profile_id=child.id,
        owner_user_id=owner.id,
        parent_chart_id=parent_chart.id,
        child_chart_version_id=chart.id,
        generation_id=generation_id,
        operation="generate",
        idempotency_key="graph-generation",
        status="ready",
        diagnostics={},
    )
    db_session.add_all([questionnaire, generation])
    await db_session.flush()
    db_session.add_all(
        [
            models.ChildAnswer(
                child_profile_id=child.id,
                questionnaire_session_id=questionnaire.id,
                question_key="support",
                answer={"value": "pause"},
                answer_version="answer-v1",
            ),
            models.ChildParentStyleScore(
                child_profile_id=child.id,
                parent_chart_id=parent_chart.id,
                generation_id=generation_id,
                dimension="structure",
                score=60,
                confidence=0.8,
                scoring_version="score-v1",
                breakdown={},
                evidence_refs=["parent:1"],
            ),
            models.ChildNeedScore(
                child_profile_id=child.id,
                child_chart_version_id=chart.id,
                generation_id=generation_id,
                dimension="predictability",
                score=65,
                confidence=0.75,
                scoring_version="score-v1",
                breakdown={},
                evidence_refs=["child:1"],
            ),
            models.ChildSynastryEvidence(
                child_profile_id=child.id,
                parent_chart_id=parent_chart.id,
                child_chart_version_id=chart.id,
                generation_id=generation_id,
                source_type="aspect",
                source_key="sun-moon",
                contribution=0.4,
                direction="support",
                payload={"orb": 2.0},
            ),
            models.ChildInteractionScore(
                child_profile_id=child.id,
                parent_chart_id=parent_chart.id,
                child_chart_version_id=chart.id,
                generation_id=generation_id,
                dimension="boundary_fit",
                score=55,
                confidence=0.7,
                pattern="balanced",
                scoring_version="score-v1",
                evidence_refs=["synastry:1"],
                breakdown={},
            ),
            models.ChildContextResolution(
                child_profile_id=child.id,
                generation_id=generation_id,
                resolver_version="resolver-v1",
                natural_strengths=["calm"],
                potential_friction=["pace"],
                compensation_areas=[],
                age_relevant_guidance=["short_steps"],
                confirmations=[],
                contradictions=[],
                unresolved_ambiguities=[],
            ),
            models.ChildGuidanceFacts(
                child_profile_id=child.id,
                generation_id=generation_id,
                age_snapshot_id=age.id,
                contract_version="facts-v1",
                core_report_version=1,
                payload={"action": "pause"},
                evidence_registry={"action": ["synastry:1"]},
            ),
            models.ChildSegmentGeneration(
                child_profile_id=child.id,
                generation_id=generation_id,
                section_key="summary",
                status="ready",
                prompt_version="prompt-v1",
                model="mock",
                content="Persisted section",
                evidence_refs=["facts:1"],
                diagnostics={},
            ),
        ]
    )
    report = models.ChildReport(
        child_profile_id=child.id,
        parent_chart_id=parent_chart.id,
        child_chart_version_id=chart.id,
        generation_id=generation_id,
        idempotency_key="graph-report",
        version=1,
        status="ready",
        scoring_version="score-v1",
        reference_version="reference-v1",
        questionnaire_version="q-v1",
        prompt_version="prompt-v1",
        report_payload={"summary": "persisted"},
        presentation_manifest={"sections": ["summary"]},
    )
    db_session.add(report)
    await db_session.flush()
    generation.report_id = report.id
    db_session.add(
        models.ChildReportAgeGuidance(
            child_profile_id=child.id,
            report_id=report.id,
            age_snapshot_id=age.id,
            version=1,
            idempotency_key="graph-age-guidance",
            status="ready",
            rules_version="age-guidance-v1",
            payload={"actions": ["pause"]},
        )
    )
    await db_session.commit()
    return owner, parent_profile, parent_chart, child, sibling, report


@pytest.mark.asyncio
async def test_immutable_artifacts_reject_update_and_direct_delete(db_session: AsyncSession) -> None:
    _, _, _, child, _, report = await _seed_complete_graph(db_session)
    child_id = child.id
    report.report_payload = {"summary": "mutated"}
    with pytest.raises(models.ImmutableChildArtifactError):
        await db_session.commit()
    await db_session.rollback()

    chart = await db_session.scalar(
        select(models.ChildChartVersion).where(models.ChildChartVersion.child_profile_id == child_id)
    )
    assert chart is not None
    await db_session.delete(chart)
    with pytest.raises(models.ImmutableChildArtifactError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_full_artifact_graph_reconstructs_from_fresh_postgresql_session(db_session: AsyncSession) -> None:
    owner, _, _, child, _, report = await _seed_complete_graph(db_session)
    assert isinstance(db_session.bind, AsyncEngine)
    sessions = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)
    async with sessions() as fresh_session:
        graph = await ChildRepository(fresh_session).load_report_graph(
            owner_user_id=owner.id,
            child_profile_id=child.id,
            report_id=report.id,
        )

    assert graph.report.report_payload == {"summary": "persisted"}
    assert graph.child_chart.calculation_payload == {"planets": ["sun"]}
    assert len(graph.parent_style_scores) == 1
    assert len(graph.child_need_scores) == 1
    assert len(graph.synastry_evidence) == 1
    assert len(graph.interaction_scores) == 1
    assert len(graph.questionnaires) == 1
    assert len(graph.answers) == 1
    assert len(graph.context_resolutions) == 1
    assert len(graph.guidance_facts) == 1
    assert len(graph.segment_generations) == 1
    assert len(graph.age_guidance) == 1
    assert graph.age_guidance[0].age_snapshot_id == graph.age_snapshots[0].id


@pytest.mark.asyncio
async def test_archive_and_purge_delete_full_child_graph_but_preserve_owner_and_sibling(
    db_session: AsyncSession,
) -> None:
    owner, parent_profile, parent_chart, child, sibling, _ = await _seed_complete_graph(db_session)
    repository = ChildRepository(db_session)
    archived = await repository.archive_child(owner_user_id=owner.id, child_profile_id=child.id)
    assert archived.status == "archived"
    await db_session.commit()

    await repository.purge_child_domain(owner_user_id=owner.id, child_profile_id=child.id)
    await db_session.commit()

    assert await db_session.get(models.ChildProfile, child.id) is None
    assert await db_session.get(models.ChildProfile, sibling.id) is not None
    assert await db_session.get(User, owner.id) is not None
    assert await db_session.get(PersonProfile, parent_profile.id) is not None
    assert await db_session.get(NatalChart, parent_chart.id) is not None
    for model in models.CHILD_DOMAIN_ARTIFACT_MODELS:
        child_column = getattr(model, "child_profile_id", None)
        if child_column is not None:
            assert await db_session.scalar(select(func.count()).select_from(model).where(child_column == child.id)) == 0

    audit_count = await db_session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(AuditLog.actor_id == owner.id, AuditLog.entity_id == str(child.id))
    )
    assert audit_count == 1


@pytest.mark.asyncio
async def test_purge_is_transactional_and_rollback_restores_child_graph(db_session: AsyncSession) -> None:
    owner, _, _, child, _, _ = await _seed_complete_graph(db_session)
    owner_id = owner.id
    child_id = child.id
    before_counts = {
        model.__tablename__: await db_session.scalar(
            select(func.count()).select_from(model).where(model.child_profile_id == child_id)
        )
        for model in models.CHILD_DOMAIN_ARTIFACT_MODELS
    }
    await ChildRepository(db_session).purge_child_domain(owner_user_id=owner.id, child_profile_id=child_id)
    await db_session.rollback()

    restored_child = await db_session.get(models.ChildProfile, child_id)
    assert restored_child is not None
    assert restored_child.status == "active"
    after_counts = {
        model.__tablename__: await db_session.scalar(
            select(func.count()).select_from(model).where(model.child_profile_id == child_id)
        )
        for model in models.CHILD_DOMAIN_ARTIFACT_MODELS
    }
    assert after_counts == before_counts
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.actor_id == owner_id, AuditLog.entity_id == str(child_id))
        )
        == 0
    )
