"""Persistence boundary for owner-scoped immutable Child Report artifacts."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any, TypeVar, cast
from uuid import UUID

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog
from app.core.models import BaseModel
from app.modules.astrotype_v2.models import NatalChart
from app.modules.child import models
from app.modules.child.chart_adapter import ChildChartBuild
from app.modules.profiles.models import PersonProfile

_ChildModel = TypeVar("_ChildModel", bound=BaseModel)


class ChildIdempotencyTargetMismatchError(ValueError):
    """An idempotency key was reused for a different child target."""


class ChildLineageMismatchError(ValueError):
    """Referenced owner, child, chart, session, report, or snapshot lineage does not match."""


@dataclass(frozen=True)
class ChildProfileCreateResult:
    child: models.ChildProfile
    created: bool


@dataclass(frozen=True)
class ChildChartVersionCreateResult:
    chart: models.ChildChartVersion
    created: bool


@dataclass(frozen=True)
class ChildGenerationCreateResult:
    generation: models.ChildGeneration
    created: bool


@dataclass(frozen=True)
class ChildQuestionnaireCompletionResult:
    questionnaire: models.ChildQuestionnaireSession
    completed_now: bool


@dataclass(frozen=True)
class ChildReportCreateResult:
    report: models.ChildReport
    created: bool


@dataclass(frozen=True)
class ChildAgeGuidanceCreateResult:
    guidance: models.ChildReportAgeGuidance
    created: bool


@dataclass(frozen=True)
class ChildReportGraph:
    child: models.ChildProfile
    child_chart: models.ChildChartVersion
    generation: models.ChildGeneration
    report: models.ChildReport
    age_snapshots: tuple[models.ChildAgeSnapshot, ...]
    parent_style_scores: tuple[models.ChildParentStyleScore, ...]
    child_need_scores: tuple[models.ChildNeedScore, ...]
    synastry_evidence: tuple[models.ChildSynastryEvidence, ...]
    interaction_scores: tuple[models.ChildInteractionScore, ...]
    questionnaires: tuple[models.ChildQuestionnaireSession, ...]
    answers: tuple[models.ChildAnswer, ...]
    context_resolutions: tuple[models.ChildContextResolution, ...]
    guidance_facts: tuple[models.ChildGuidanceFacts, ...]
    segment_generations: tuple[models.ChildSegmentGeneration, ...]
    age_guidance: tuple[models.ChildReportAgeGuidance, ...]


class ChildRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, instance: _ChildModel) -> _ChildModel:
        self.session.add(instance)
        return instance

    async def add_many(self, instances: Sequence[_ChildModel]) -> Sequence[_ChildModel]:
        self.session.add_all(list(instances))
        return instances

    async def flush(self) -> None:
        await self.session.flush()

    async def _require_owned_child(self, *, child_profile_id: UUID, owner_user_id: UUID) -> models.ChildProfile:
        child = await self.session.scalar(
            select(models.ChildProfile).where(
                models.ChildProfile.id == child_profile_id,
                models.ChildProfile.owner_user_id == owner_user_id,
            )
        )
        if child is None:
            raise ChildLineageMismatchError("Child profile is not owned by the requested owner")
        return child

    async def _require_parent_profile_owner(self, *, parent_profile_id: UUID, owner_user_id: UUID) -> None:
        profile_id = await self.session.scalar(
            select(PersonProfile.id).where(
                PersonProfile.id == parent_profile_id,
                PersonProfile.user_id == owner_user_id,
            )
        )
        if profile_id is None:
            raise ChildLineageMismatchError("Parent profile is not owned by the requested owner")

    async def _require_parent_chart_owner(
        self,
        *,
        parent_chart_id: UUID,
        parent_profile_id: UUID,
        owner_user_id: UUID,
    ) -> None:
        chart_id = await self.session.scalar(
            select(NatalChart.id).where(
                NatalChart.id == parent_chart_id,
                NatalChart.profile_id == parent_profile_id,
                NatalChart.user_id == owner_user_id,
            )
        )
        if chart_id is None:
            raise ChildLineageMismatchError("Parent chart does not match the owner and parent profile")

    async def _require_child_chart(
        self,
        *,
        child_chart_version_id: UUID,
        child_profile_id: UUID,
    ) -> None:
        chart_id = await self.session.scalar(
            select(models.ChildChartVersion.id).where(
                models.ChildChartVersion.id == child_chart_version_id,
                models.ChildChartVersion.child_profile_id == child_profile_id,
            )
        )
        if chart_id is None:
            raise ChildLineageMismatchError("Child chart version does not belong to the child")

    async def get_child_by_idempotency_key(
        self,
        *,
        owner_user_id: UUID,
        idempotency_key: str,
    ) -> models.ChildProfile | None:
        result = await self.session.execute(
            select(models.ChildProfile).where(
                models.ChildProfile.owner_user_id == owner_user_id,
                models.ChildProfile.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def create_child_idempotently(
        self,
        *,
        owner_user_id: UUID,
        parent_profile_id: UUID,
        display_name: str,
        relationship_type: str,
        child_gender: str | None,
        birth_date: date,
        birth_time: time | None,
        birth_time_confidence: str,
        birth_place: str,
        latitude: float,
        longitude: float,
        timezone: str,
        caregiver_context: dict[str, Any],
        birth_data_hash: str,
        idempotency_key: str,
    ) -> ChildProfileCreateResult:
        await self._require_parent_profile_owner(
            parent_profile_id=parent_profile_id,
            owner_user_id=owner_user_id,
        )
        statement = (
            pg_insert(models.ChildProfile)
            .values(
                id=uuid.uuid4(),
                owner_user_id=owner_user_id,
                parent_profile_id=parent_profile_id,
                display_name=display_name,
                relationship_type=relationship_type,
                child_gender=child_gender,
                birth_date=birth_date,
                birth_time=birth_time,
                birth_time_confidence=birth_time_confidence,
                birth_place=birth_place,
                latitude=latitude,
                longitude=longitude,
                timezone=timezone,
                caregiver_context=caregiver_context,
                birth_data_hash=birth_data_hash,
                idempotency_key=idempotency_key,
                status="active",
                version=1,
            )
            .on_conflict_do_nothing(constraint="uq_child_profiles_owner_idempotency")
            .returning(models.ChildProfile)
        )
        inserted = (await self.session.execute(statement)).scalar_one_or_none()
        if inserted is not None:
            return ChildProfileCreateResult(child=inserted, created=True)

        existing = await self.get_child_by_idempotency_key(
            owner_user_id=owner_user_id,
            idempotency_key=idempotency_key,
        )
        if existing is None:
            raise RuntimeError("Child profile conflict could not be read back")
        if (existing.parent_profile_id, existing.birth_data_hash) != (parent_profile_id, birth_data_hash):
            raise ChildIdempotencyTargetMismatchError("Idempotency key already used for another child target")
        return ChildProfileCreateResult(child=existing, created=False)

    async def create_generation_idempotently(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        parent_chart_id: UUID,
        child_chart_version_id: UUID,
        operation: str,
        idempotency_key: str,
        source_report_id: UUID | None = None,
    ) -> ChildGenerationCreateResult:
        child = await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
        )
        await self._require_parent_chart_owner(
            parent_chart_id=parent_chart_id,
            parent_profile_id=child.parent_profile_id,
            owner_user_id=owner_user_id,
        )
        await self._require_child_chart(
            child_chart_version_id=child_chart_version_id,
            child_profile_id=child_profile_id,
        )
        if source_report_id is not None:
            source_child_id = await self.session.scalar(
                select(models.ChildReport.child_profile_id).where(models.ChildReport.id == source_report_id)
            )
            if source_child_id != child_profile_id:
                raise ChildLineageMismatchError("Source report does not belong to the child")

        statement = (
            pg_insert(models.ChildGeneration)
            .values(
                id=uuid.uuid4(),
                child_profile_id=child_profile_id,
                owner_user_id=owner_user_id,
                parent_chart_id=parent_chart_id,
                child_chart_version_id=child_chart_version_id,
                generation_id=uuid.uuid4(),
                operation=operation,
                idempotency_key=idempotency_key,
                status="queued",
                source_report_id=source_report_id,
                diagnostics={},
            )
            .on_conflict_do_nothing(constraint="uq_child_generations_owner_operation_idempotency")
            .returning(models.ChildGeneration)
        )
        inserted = (await self.session.execute(statement)).scalar_one_or_none()
        if inserted is not None:
            return ChildGenerationCreateResult(generation=inserted, created=True)

        existing = await self.session.scalar(
            select(models.ChildGeneration).where(
                models.ChildGeneration.owner_user_id == owner_user_id,
                models.ChildGeneration.operation == operation,
                models.ChildGeneration.idempotency_key == idempotency_key,
            )
        )
        if existing is None:
            raise RuntimeError("Generation conflict could not be read back")
        target = (
            existing.child_profile_id,
            existing.parent_chart_id,
            existing.child_chart_version_id,
            existing.source_report_id,
        )
        expected = (child_profile_id, parent_chart_id, child_chart_version_id, source_report_id)
        if target != expected:
            raise ChildIdempotencyTargetMismatchError("Generation idempotency key was reused for another target")
        return ChildGenerationCreateResult(generation=existing, created=False)

    async def create_chart_version_idempotently(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        chart: ChildChartBuild,
    ) -> ChildChartVersionCreateResult:
        """Append one chart lineage row, serializing version allocation per child."""
        await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
        )
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": str(child_profile_id)},
        )
        existing = await self.session.scalar(
            select(models.ChildChartVersion).where(
                models.ChildChartVersion.child_profile_id == child_profile_id,
                models.ChildChartVersion.engine_version == chart.engine_version,
                models.ChildChartVersion.input_hash == chart.input_hash,
            )
        )
        if existing is not None:
            return ChildChartVersionCreateResult(chart=existing, created=False)

        latest_version = await self.session.scalar(
            select(func.max(models.ChildChartVersion.version)).where(
                models.ChildChartVersion.child_profile_id == child_profile_id
            )
        )
        statement = (
            pg_insert(models.ChildChartVersion)
            .values(
                id=uuid.uuid4(),
                child_profile_id=child_profile_id,
                version=(latest_version or 0) + 1,
                engine_version=chart.engine_version,
                input_hash=chart.input_hash,
                birth_time_confidence=chart.birth_time_confidence,
                allowed_fact_families=list(chart.allowed_fact_families),
                excluded_fact_families=list(chart.excluded_fact_families),
                uncertainty_reason=chart.uncertainty_reason,
                calculation_payload=chart.calculation_payload,
            )
            .on_conflict_do_nothing(constraint="uq_child_chart_versions_profile_engine_input")
            .returning(models.ChildChartVersion)
        )
        inserted = (await self.session.execute(statement)).scalar_one_or_none()
        if inserted is not None:
            return ChildChartVersionCreateResult(chart=inserted, created=True)

        existing = await self.session.scalar(
            select(models.ChildChartVersion).where(
                models.ChildChartVersion.child_profile_id == child_profile_id,
                models.ChildChartVersion.engine_version == chart.engine_version,
                models.ChildChartVersion.input_hash == chart.input_hash,
            )
        )
        if existing is None:
            raise RuntimeError("Child chart conflict could not be read back")
        return ChildChartVersionCreateResult(chart=existing, created=False)

    async def correct_birth_data_and_create_chart(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        birth_date: date,
        birth_time: time | None,
        birth_time_confidence: str,
        birth_place: str,
        latitude: float,
        longitude: float,
        timezone: str,
        birth_data_hash: str,
        chart: ChildChartBuild,
    ) -> ChildChartVersionCreateResult:
        """Atomically update current birth data and append, never overwrite, chart lineage."""
        if chart.birth_time_confidence != birth_time_confidence:
            raise ChildLineageMismatchError("Chart confidence does not match corrected birth data")
        if birth_time_confidence == "unknown" and birth_time is not None:
            raise ValueError("Unknown birth time must be omitted")
        if birth_time_confidence != "unknown" and birth_time is None:
            raise ValueError("Exact or approximate birth time is required")

        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": str(child_profile_id)},
        )
        child = await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
        )
        birth_data_changed = child.birth_data_hash != birth_data_hash
        if birth_data_changed:
            child.birth_date = birth_date
            child.birth_time = birth_time
            child.birth_time_confidence = birth_time_confidence
            child.birth_place = birth_place
            child.latitude = latitude
            child.longitude = longitude
            child.timezone = timezone
            child.birth_data_hash = birth_data_hash
            child.version += 1
            await self.session.flush()

        result = await self.create_chart_version_idempotently(
            owner_user_id=owner_user_id,
            child_profile_id=child_profile_id,
            chart=chart,
        )
        if birth_data_changed and not result.created:
            raise ChildIdempotencyTargetMismatchError(
                "Corrected birth data must create a new child chart input lineage"
            )
        return result

    async def complete_questionnaire_idempotently(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        questionnaire_session_id: UUID,
        completion_idempotency_key: str,
        answers_hash: str,
        completed_at: datetime,
    ) -> ChildQuestionnaireCompletionResult:
        await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
        )
        statement = (
            update(models.ChildQuestionnaireSession)
            .where(
                models.ChildQuestionnaireSession.id == questionnaire_session_id,
                models.ChildQuestionnaireSession.child_profile_id == child_profile_id,
                models.ChildQuestionnaireSession.status == "draft",
            )
            .values(
                status="completed",
                completion_idempotency_key=completion_idempotency_key,
                answers_hash=answers_hash,
                completed_at=completed_at,
            )
            .returning(models.ChildQuestionnaireSession)
        )
        completed = (await self.session.execute(statement)).scalar_one_or_none()
        if completed is not None:
            return ChildQuestionnaireCompletionResult(questionnaire=completed, completed_now=True)

        existing = await self.session.scalar(
            select(models.ChildQuestionnaireSession).where(
                models.ChildQuestionnaireSession.id == questionnaire_session_id,
                models.ChildQuestionnaireSession.child_profile_id == child_profile_id,
            )
        )
        if existing is None:
            raise ChildLineageMismatchError("Questionnaire session does not belong to the child")
        if (
            existing.status != "completed"
            or existing.completion_idempotency_key != completion_idempotency_key
            or existing.answers_hash != answers_hash
        ):
            raise ChildIdempotencyTargetMismatchError("Questionnaire completion key was reused for another answer set")
        return ChildQuestionnaireCompletionResult(questionnaire=existing, completed_now=False)

    async def create_report_idempotently(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        generation_id: UUID,
        parent_chart_id: UUID,
        child_chart_version_id: UUID,
        idempotency_key: str,
        version: int,
        status: str,
        scoring_version: str,
        reference_version: str,
        questionnaire_version: str,
        prompt_version: str,
        report_payload: dict[str, Any],
        presentation_manifest: dict[str, Any],
    ) -> ChildReportCreateResult:
        await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
        )
        generation = await self.session.scalar(
            select(models.ChildGeneration).where(
                models.ChildGeneration.generation_id == generation_id,
                models.ChildGeneration.child_profile_id == child_profile_id,
                models.ChildGeneration.owner_user_id == owner_user_id,
            )
        )
        if generation is None or (
            generation.parent_chart_id != parent_chart_id or generation.child_chart_version_id != child_chart_version_id
        ):
            raise ChildLineageMismatchError("Report target does not match generation lineage")

        statement = (
            pg_insert(models.ChildReport)
            .values(
                id=uuid.uuid4(),
                child_profile_id=child_profile_id,
                parent_chart_id=parent_chart_id,
                child_chart_version_id=child_chart_version_id,
                generation_id=generation_id,
                idempotency_key=idempotency_key,
                version=version,
                status=status,
                scoring_version=scoring_version,
                reference_version=reference_version,
                questionnaire_version=questionnaire_version,
                prompt_version=prompt_version,
                report_payload=report_payload,
                presentation_manifest=presentation_manifest,
            )
            .on_conflict_do_nothing()
            .returning(models.ChildReport)
        )
        inserted = (await self.session.execute(statement)).scalar_one_or_none()
        if inserted is not None:
            return ChildReportCreateResult(report=inserted, created=True)

        existing = await self.session.scalar(
            select(models.ChildReport).where(
                models.ChildReport.child_profile_id == child_profile_id,
                models.ChildReport.idempotency_key == idempotency_key,
            )
        )
        if existing is None:
            raise ChildIdempotencyTargetMismatchError("Report generation already produced a different target")
        target = (
            existing.generation_id,
            existing.parent_chart_id,
            existing.child_chart_version_id,
            existing.version,
        )
        expected = (generation_id, parent_chart_id, child_chart_version_id, version)
        if target != expected:
            raise ChildIdempotencyTargetMismatchError("Report idempotency key was reused for another target")
        return ChildReportCreateResult(report=existing, created=False)

    async def create_age_guidance_idempotently(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        report_id: UUID,
        age_snapshot_id: UUID,
        version: int,
        idempotency_key: str,
        status: str,
        rules_version: str,
        payload: dict[str, Any],
    ) -> ChildAgeGuidanceCreateResult:
        await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
        )
        report_child_id = await self.session.scalar(
            select(models.ChildReport.child_profile_id).where(models.ChildReport.id == report_id)
        )
        snapshot_child_id = await self.session.scalar(
            select(models.ChildAgeSnapshot.child_profile_id).where(models.ChildAgeSnapshot.id == age_snapshot_id)
        )
        if report_child_id != child_profile_id or snapshot_child_id != child_profile_id:
            raise ChildLineageMismatchError("Age guidance report or snapshot does not belong to the child")

        statement = (
            pg_insert(models.ChildReportAgeGuidance)
            .values(
                id=uuid.uuid4(),
                child_profile_id=child_profile_id,
                report_id=report_id,
                age_snapshot_id=age_snapshot_id,
                version=version,
                idempotency_key=idempotency_key,
                status=status,
                rules_version=rules_version,
                payload=payload,
            )
            .on_conflict_do_nothing()
            .returning(models.ChildReportAgeGuidance)
        )
        inserted = (await self.session.execute(statement)).scalar_one_or_none()
        if inserted is not None:
            return ChildAgeGuidanceCreateResult(guidance=inserted, created=True)

        existing = await self.session.scalar(
            select(models.ChildReportAgeGuidance).where(
                models.ChildReportAgeGuidance.child_profile_id == child_profile_id,
                models.ChildReportAgeGuidance.idempotency_key == idempotency_key,
            )
        )
        if existing is None:
            raise RuntimeError("Age guidance conflict could not be read back")
        if (existing.report_id, existing.age_snapshot_id, existing.version) != (
            report_id,
            age_snapshot_id,
            version,
        ):
            raise ChildIdempotencyTargetMismatchError("Age guidance key was reused for another target")
        return ChildAgeGuidanceCreateResult(guidance=existing, created=False)

    async def archive_child(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
    ) -> models.ChildProfile:
        archived = (
            await self.session.execute(
                update(models.ChildProfile)
                .where(
                    models.ChildProfile.id == child_profile_id,
                    models.ChildProfile.owner_user_id == owner_user_id,
                    models.ChildProfile.status != "deletion_pending",
                )
                .values(status="archived", archived_at=datetime.now().astimezone())
                .returning(models.ChildProfile)
            )
        ).scalar_one_or_none()
        if archived is None:
            raise ChildLineageMismatchError("Child profile is not owned by the requested owner")
        return archived

    async def purge_child_domain(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
    ) -> None:
        child = await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
        )
        child.status = "deletion_pending"
        await self.session.flush()
        await self.session.execute(text("SET LOCAL app.child_purge = 'on'"))
        deleted_id = await self.session.scalar(
            delete(models.ChildProfile)
            .where(
                models.ChildProfile.id == child_profile_id,
                models.ChildProfile.owner_user_id == owner_user_id,
            )
            .returning(models.ChildProfile.id)
        )
        if deleted_id is None:
            raise ChildLineageMismatchError("Child profile is not owned by the requested owner")
        self.session.add(
            AuditLog(
                actor_id=owner_user_id,
                action="child_hard_delete",
                entity_type="child_profile",
                entity_id=str(child_profile_id),
                changes={
                    "event_type": "child_hard_delete",
                    "owner_user_id": str(owner_user_id),
                    "child_profile_id": str(child_profile_id),
                    "result": "deleted",
                },
            )
        )

    async def load_report_graph(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        report_id: UUID,
    ) -> ChildReportGraph:
        child = await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
        )
        report = await self.session.scalar(
            select(models.ChildReport).where(
                models.ChildReport.id == report_id,
                models.ChildReport.child_profile_id == child_profile_id,
            )
        )
        if report is None:
            raise ChildLineageMismatchError("Report does not belong to the child")
        generation = await self.session.scalar(
            select(models.ChildGeneration).where(
                models.ChildGeneration.child_profile_id == child_profile_id,
                models.ChildGeneration.generation_id == report.generation_id,
            )
        )
        child_chart = await self.session.scalar(
            select(models.ChildChartVersion).where(
                models.ChildChartVersion.child_profile_id == child_profile_id,
                models.ChildChartVersion.id == report.child_chart_version_id,
            )
        )
        if generation is None or child_chart is None:
            raise ChildLineageMismatchError("Persisted report lineage is incomplete")

        async def rows(model: type[_ChildModel], *criteria: Any) -> tuple[Any, ...]:
            result = await self.session.execute(select(model).where(*criteria))
            return tuple(result.scalars().all())

        questionnaires = cast(
            tuple[models.ChildQuestionnaireSession, ...],
            await rows(
                models.ChildQuestionnaireSession,
                models.ChildQuestionnaireSession.child_profile_id == child_profile_id,
                models.ChildQuestionnaireSession.questionnaire_version == report.questionnaire_version,
            ),
        )
        questionnaire_ids = [questionnaire.id for questionnaire in questionnaires]
        answers: tuple[models.ChildAnswer, ...] = ()
        if questionnaire_ids:
            answers = cast(
                tuple[models.ChildAnswer, ...],
                await rows(
                    models.ChildAnswer,
                    models.ChildAnswer.child_profile_id == child_profile_id,
                    models.ChildAnswer.questionnaire_session_id.in_(questionnaire_ids),
                ),
            )

        return ChildReportGraph(
            child=child,
            child_chart=child_chart,
            generation=generation,
            report=report,
            age_snapshots=cast(
                tuple[models.ChildAgeSnapshot, ...],
                await rows(models.ChildAgeSnapshot, models.ChildAgeSnapshot.child_profile_id == child_profile_id),
            ),
            parent_style_scores=cast(
                tuple[models.ChildParentStyleScore, ...],
                await rows(
                    models.ChildParentStyleScore,
                    models.ChildParentStyleScore.child_profile_id == child_profile_id,
                    models.ChildParentStyleScore.generation_id == report.generation_id,
                ),
            ),
            child_need_scores=cast(
                tuple[models.ChildNeedScore, ...],
                await rows(
                    models.ChildNeedScore,
                    models.ChildNeedScore.child_profile_id == child_profile_id,
                    models.ChildNeedScore.generation_id == report.generation_id,
                ),
            ),
            synastry_evidence=cast(
                tuple[models.ChildSynastryEvidence, ...],
                await rows(
                    models.ChildSynastryEvidence,
                    models.ChildSynastryEvidence.child_profile_id == child_profile_id,
                    models.ChildSynastryEvidence.generation_id == report.generation_id,
                ),
            ),
            interaction_scores=cast(
                tuple[models.ChildInteractionScore, ...],
                await rows(
                    models.ChildInteractionScore,
                    models.ChildInteractionScore.child_profile_id == child_profile_id,
                    models.ChildInteractionScore.generation_id == report.generation_id,
                ),
            ),
            questionnaires=questionnaires,
            answers=answers,
            context_resolutions=cast(
                tuple[models.ChildContextResolution, ...],
                await rows(
                    models.ChildContextResolution,
                    models.ChildContextResolution.child_profile_id == child_profile_id,
                    models.ChildContextResolution.generation_id == report.generation_id,
                ),
            ),
            guidance_facts=cast(
                tuple[models.ChildGuidanceFacts, ...],
                await rows(
                    models.ChildGuidanceFacts,
                    models.ChildGuidanceFacts.child_profile_id == child_profile_id,
                    models.ChildGuidanceFacts.generation_id == report.generation_id,
                ),
            ),
            segment_generations=cast(
                tuple[models.ChildSegmentGeneration, ...],
                await rows(
                    models.ChildSegmentGeneration,
                    models.ChildSegmentGeneration.child_profile_id == child_profile_id,
                    models.ChildSegmentGeneration.generation_id == report.generation_id,
                ),
            ),
            age_guidance=cast(
                tuple[models.ChildReportAgeGuidance, ...],
                await rows(
                    models.ChildReportAgeGuidance,
                    models.ChildReportAgeGuidance.child_profile_id == child_profile_id,
                    models.ChildReportAgeGuidance.report_id == report_id,
                ),
            ),
        )

    async def get_child_for_owner(
        self,
        *,
        child_id: UUID,
        owner_user_id: UUID,
        include_archived: bool = False,
    ) -> models.ChildProfile | None:
        statement = select(models.ChildProfile).where(
            models.ChildProfile.id == child_id,
            models.ChildProfile.owner_user_id == owner_user_id,
        )
        if not include_archived:
            statement = statement.where(models.ChildProfile.status != "archived")
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_children_for_owner(
        self,
        *,
        owner_user_id: UUID,
        include_archived: bool = False,
    ) -> list[models.ChildProfile]:
        statement = select(models.ChildProfile).where(models.ChildProfile.owner_user_id == owner_user_id)
        if not include_archived:
            statement = statement.where(models.ChildProfile.status != "archived")
        result = await self.session.execute(statement.order_by(models.ChildProfile.created_at))
        return list(result.scalars().all())

    async def get_latest_chart_version(self, child_profile_id: UUID) -> models.ChildChartVersion | None:
        result = await self.session.execute(
            select(models.ChildChartVersion)
            .where(models.ChildChartVersion.child_profile_id == child_profile_id)
            .order_by(models.ChildChartVersion.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_report(
        self,
        *,
        child_profile_id: UUID,
        owner_user_id: UUID,
    ) -> models.ChildReport | None:
        result = await self.session.execute(
            select(models.ChildReport)
            .join(models.ChildProfile, models.ChildReport.child_profile_id == models.ChildProfile.id)
            .where(
                models.ChildReport.child_profile_id == child_profile_id,
                models.ChildProfile.owner_user_id == owner_user_id,
            )
            .order_by(models.ChildReport.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_owned_report_id(self, *, report_id: UUID, owner_user_id: UUID) -> UUID | None:
        """Resolve ownership without loading report payload columns."""

        return cast(
            UUID | None,
            await self.session.scalar(
                select(models.ChildReport.id)
                .join(models.ChildProfile, models.ChildReport.child_profile_id == models.ChildProfile.id)
                .where(
                    models.ChildReport.id == report_id,
                    models.ChildProfile.owner_user_id == owner_user_id,
                )
            ),
        )
