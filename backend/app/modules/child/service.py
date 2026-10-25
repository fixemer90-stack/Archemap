"""Application service for durable asynchronous Child Report generation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, Protocol, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.child import models
from app.modules.child.assembly import assemble_child_report_payload
from app.modules.child.guidance_facts import ChildGuidanceFactsRepository
from app.modules.child.narrative import (
    CHILD_PROMPT_VERSION,
    ChildSegmentProvider,
    DisabledChildSegmentProvider,
    StructuredChildSegmentProviderAdapter,
    build_child_section_inputs,
    build_child_segment_intent,
    run_child_segment_generation,
)
from app.modules.child.prompts.v1 import SECTION_METADATA
from app.modules.child.questionnaire_persistence import ChildContextResolutionRepository
from app.modules.child.repository import (
    ChildGenerationClaim,
    ChildIdempotencyTargetMismatchError,
    ChildLineageMismatchError,
    ChildRepository,
)
from app.modules.child.status import (
    CLAIMABLE_STATUSES,
    ChildGenerationOperation,
    ChildGenerationStatus,
)
from app.modules.llm.provider import get_llm_provider
from app.reference_data.child.interaction_v1 import (
    INTERACTION_REFERENCE_VERSION,
    INTERACTION_SCORING_VERSION,
)


class ChildGenerationDispatcher(Protocol):
    def __call__(self, *, generation_id: UUID) -> str: ...


@dataclass(frozen=True, slots=True)
class ChildGenerationAccepted:
    generation_id: UUID
    status: str
    report_id: UUID | None
    created: bool
    task_id: str | None


@dataclass(frozen=True, slots=True)
class ChildGenerationRunResult:
    generation_id: UUID
    status: str
    report_id: UUID | None
    provider_calls: int


def configured_child_provider() -> ChildSegmentProvider:
    """Build the configured bounded provider adapter."""

    if not settings.LLM_ENABLED or settings.LLM_PROVIDER == "mock":
        return DisabledChildSegmentProvider()
    # Child owns retries durably; never hide another POST inside one intent.
    provider = get_llm_provider(settings.model_copy(update={"LLM_MAX_RETRIES": 0}))
    return StructuredChildSegmentProviderAdapter(
        provider=provider,
        provider_name=settings.LLM_PROVIDER,
        model_name=settings.LLM_MODEL,
    )


async def _require_active_child(
    session: AsyncSession,
    *,
    owner_user_id: UUID,
    child_profile_id: UUID,
) -> None:
    child_id = await session.scalar(
        select(models.ChildProfile.id).where(
            models.ChildProfile.id == child_profile_id,
            models.ChildProfile.owner_user_id == owner_user_id,
            models.ChildProfile.status == "active",
        )
    )
    if child_id is None:
        raise ChildLineageMismatchError("Child resource is unavailable")


def _source_segment_pin(row: models.ChildSegmentGeneration) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "section_key": row.section_key,
        "status": row.status,
        "prompt_version": row.prompt_version,
        "model": row.model,
        "input_hash": row.diagnostics.get("input_hash"),
        "prompt_hash": row.diagnostics.get("prompt_hash"),
        "error_code": row.error_code,
    }


def _source_segment_pin_hash(pin: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(pin, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _guidance_facts_input_hash(row: models.ChildGuidanceFacts) -> str:
    return hashlib.sha256(
        json.dumps(
            {
                "id": str(row.id),
                "generation_id": str(row.generation_id),
                "age_snapshot_id": str(row.age_snapshot_id),
                "contract_version": row.contract_version,
                "core_report_version": row.core_report_version,
                "payload": row.payload,
                "evidence_registry": row.evidence_registry,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


async def _dispatch_accepted_generation(
    session: AsyncSession,
    *,
    repository: ChildRepository,
    generation_id: UUID,
    dispatcher: ChildGenerationDispatcher,
) -> str | None:
    claimed_at = datetime.now(UTC)
    task_id = await repository.claim_generation_dispatch(
        generation_id=generation_id,
        now=claimed_at,
        lease_duration=timedelta(seconds=settings.CHILD_GENERATION_DISPATCH_LEASE_SECONDS),
    )
    if task_id is None:
        return None
    await session.commit()
    succeeded = False
    try:
        dispatched_task_id = dispatcher(generation_id=generation_id)
        if dispatched_task_id != task_id:
            raise RuntimeError("Child generation dispatcher returned an unstable task id")
        succeeded = True
    except Exception:
        dispatched_task_id = None
    await repository.record_generation_dispatch_outcome(
        generation_id=generation_id,
        task_id=task_id,
        succeeded=succeeded,
        now=datetime.now(UTC),
    )
    await session.commit()
    return dispatched_task_id


async def accept_full_generation(
    session: AsyncSession,
    *,
    owner_user_id: UUID,
    child_profile_id: UUID,
    questionnaire_session_id: UUID,
    idempotency_key: str,
    dispatcher: ChildGenerationDispatcher,
) -> ChildGenerationAccepted:
    """Commit queued work and return without running deterministic or provider stages inline."""

    repository = ChildRepository(session)
    result = await repository.resolve_full_generation_replay(
        owner_user_id=owner_user_id,
        child_profile_id=child_profile_id,
        questionnaire_session_id=questionnaire_session_id,
        idempotency_key=idempotency_key,
    )
    if result is None:
        lineage = await repository.resolve_current_generation_lineage(
            owner_user_id=owner_user_id,
            child_profile_id=child_profile_id,
            questionnaire_session_id=questionnaire_session_id,
        )
        result = await repository.create_generation_idempotently(
            owner_user_id=owner_user_id,
            child_profile_id=child_profile_id,
            parent_chart_id=lineage.parent_chart_id,
            child_chart_version_id=lineage.child_chart_version_id,
            questionnaire_session_id=lineage.questionnaire_session_id,
            operation=ChildGenerationOperation.FULL_REPORT.value,
            idempotency_key=idempotency_key,
        )
    await session.commit()

    task_id = result.generation.celery_task_id
    if result.created:
        task_id = await _dispatch_accepted_generation(
            session,
            repository=repository,
            generation_id=result.generation.generation_id,
            dispatcher=dispatcher,
        )
    return ChildGenerationAccepted(
        generation_id=result.generation.generation_id,
        status=result.generation.status,
        report_id=result.generation.report_id,
        created=result.created,
        task_id=task_id,
    )


async def accept_age_update_generation(
    session: AsyncSession,
    *,
    owner_user_id: UUID,
    child_profile_id: UUID,
    source_report_id: UUID,
    idempotency_key: str,
    guidance_rules_version: str,
    payload: dict[str, Any],
    dispatcher: ChildGenerationDispatcher,
    now: datetime | None = None,
) -> ChildGenerationAccepted:
    """Persist an age-only job without invoking pair or narrative generation."""

    await _require_active_child(
        session,
        owner_user_id=owner_user_id,
        child_profile_id=child_profile_id,
    )
    existing = await session.scalar(
        select(models.ChildGeneration).where(
            models.ChildGeneration.owner_user_id == owner_user_id,
            models.ChildGeneration.operation == ChildGenerationOperation.AGE_UPDATE.value,
            models.ChildGeneration.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if (
            existing.child_profile_id != child_profile_id
            or existing.source_report_id != source_report_id
            or existing.operation_payload.get("guidance_rules_version") != guidance_rules_version
            or existing.operation_payload.get("payload") != payload
        ):
            raise ChildIdempotencyTargetMismatchError("Age update idempotency key was reused for another target")
        return ChildGenerationAccepted(
            generation_id=existing.generation_id,
            status=existing.status,
            report_id=source_report_id,
            created=False,
            task_id=existing.celery_task_id,
        )

    source_report = await session.scalar(
        select(models.ChildReport).where(
            models.ChildReport.id == source_report_id,
            models.ChildReport.child_profile_id == child_profile_id,
        )
    )
    if source_report is None:
        raise ChildLineageMismatchError("Source report is unavailable")
    source_generation = await session.scalar(
        select(models.ChildGeneration).where(
            models.ChildGeneration.generation_id == source_report.generation_id,
            models.ChildGeneration.owner_user_id == owner_user_id,
        )
    )
    if source_generation is None:
        raise ChildLineageMismatchError("Source generation is unavailable")
    repository = ChildRepository(session)
    snapshot_result = await repository.create_age_snapshot_idempotently(
        owner_user_id=owner_user_id,
        child_profile_id=child_profile_id,
        now=now,
    )
    guidance_input_hash = hashlib.sha256(
        json.dumps(
            {
                "age_snapshot_id": str(snapshot_result.snapshot.id),
                "age_input_hash": snapshot_result.snapshot.input_hash,
                "age_rules_version": snapshot_result.snapshot.age_rules_version,
                "guidance_rules_version": guidance_rules_version,
                "payload": payload,
                "source_generation_id": str(source_generation.generation_id),
                "source_report_id": str(source_report_id),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    result = await repository.create_generation_idempotently(
        owner_user_id=owner_user_id,
        child_profile_id=child_profile_id,
        parent_chart_id=source_generation.parent_chart_id,
        child_chart_version_id=source_generation.child_chart_version_id,
        questionnaire_session_id=source_generation.questionnaire_session_id,
        operation=ChildGenerationOperation.AGE_UPDATE.value,
        idempotency_key=idempotency_key,
        source_report_id=source_report_id,
        operation_payload={
            "age_snapshot_id": str(snapshot_result.snapshot.id),
            "age_input_hash": snapshot_result.snapshot.input_hash,
            "age_rules_version": snapshot_result.snapshot.age_rules_version,
            "guidance_rules_version": guidance_rules_version,
            "guidance_input_hash": guidance_input_hash,
            "source_generation_id": str(source_generation.generation_id),
            "source_report_id": str(source_report_id),
            "payload": payload,
        },
    )
    await session.commit()
    task_id = result.generation.celery_task_id
    if result.created:
        task_id = await _dispatch_accepted_generation(
            session,
            repository=repository,
            generation_id=result.generation.generation_id,
            dispatcher=dispatcher,
        )
    return ChildGenerationAccepted(
        generation_id=result.generation.generation_id,
        status=result.generation.status,
        report_id=source_report_id,
        created=result.created,
        task_id=task_id,
    )


async def accept_narrative_retry_generation(
    session: AsyncSession,
    *,
    owner_user_id: UUID,
    child_profile_id: UUID,
    source_report_id: UUID,
    idempotency_key: str,
    dispatcher: ChildGenerationDispatcher,
    now: datetime | None = None,
    scope: Literal["failed_sections", "narrative_all"] = "failed_sections",
) -> ChildGenerationAccepted:
    """Accept a pinned failed-only retry or an explicit new narrative version."""

    del dispatcher  # reconciliation publishes retries only after durable backoff
    await _require_active_child(
        session,
        owner_user_id=owner_user_id,
        child_profile_id=child_profile_id,
    )
    source_report = await session.scalar(
        select(models.ChildReport).where(
            models.ChildReport.id == source_report_id,
            models.ChildReport.child_profile_id == child_profile_id,
        )
    )
    if source_report is None:
        raise ChildLineageMismatchError("Source report is unavailable")
    source_generation = await session.scalar(
        select(models.ChildGeneration).where(
            models.ChildGeneration.generation_id == source_report.generation_id,
            models.ChildGeneration.owner_user_id == owner_user_id,
            models.ChildGeneration.child_profile_id == child_profile_id,
        )
    )
    allowed_source_statuses = {ChildGenerationStatus.NARRATIVE_FAILED.value}
    if scope == "narrative_all":
        allowed_source_statuses.add(ChildGenerationStatus.READY.value)
    if source_generation is None or source_generation.status not in allowed_source_statuses:
        raise ChildLineageMismatchError("Source narrative generation is not retryable")
    unknown_retry = await session.scalar(
        select(models.ChildSegmentGeneration.id)
        .join(
            models.ChildGeneration, models.ChildGeneration.generation_id == models.ChildSegmentGeneration.generation_id
        )
        .where(
            models.ChildGeneration.source_report_id == source_report_id,
            models.ChildGeneration.operation == ChildGenerationOperation.NARRATIVE_RETRY.value,
            models.ChildGeneration.idempotency_key != idempotency_key,
            models.ChildSegmentGeneration.error_code == "child_narrative_provider_outcome_unknown",
        )
        .limit(1)
    )
    if unknown_retry is not None:
        raise ChildLineageMismatchError("Source narrative retry has an unknown provider outcome")
    facts_row = await session.scalar(
        select(models.ChildGuidanceFacts).where(
            models.ChildGuidanceFacts.child_profile_id == child_profile_id,
            models.ChildGuidanceFacts.generation_id == source_generation.generation_id,
            models.ChildGuidanceFacts.core_report_version == source_report.version,
        )
    )
    if facts_row is None:
        raise ChildLineageMismatchError("Source guidance facts are unavailable")
    failed_segments = tuple(
        (
            await session.scalars(
                select(models.ChildSegmentGeneration)
                .where(
                    models.ChildSegmentGeneration.generation_id == source_generation.generation_id,
                    models.ChildSegmentGeneration.status.in_(
                        ["failed", "ready", "not_applicable"] if scope == "narrative_all" else ["failed"]
                    ),
                )
                .order_by(models.ChildSegmentGeneration.section_key, models.ChildSegmentGeneration.id)
            )
        ).all()
    )
    if not failed_segments:
        raise ChildLineageMismatchError("Source generation has no failed narrative sections")
    failed_section_pins = []
    for segment in failed_segments:
        pin = _source_segment_pin(segment)
        failed_section_pins.append(pin | {"pin_hash": _source_segment_pin_hash(pin)})
    repository = ChildRepository(session)
    source_segments = await repository.list_segment_generations(
        child_profile_id=child_profile_id, generation_id=source_generation.generation_id
    )
    source_keys = {row.section_key for row in source_segments}
    guidance_facts = await ChildGuidanceFactsRepository(session).load_domain_facts(
        owner_user_id=owner_user_id,
        child_profile_id=child_profile_id,
        generation_id=source_generation.generation_id,
        core_report_version=source_report.version,
    )
    missing_section_pins = [
        {"section_key": item.section_key, "input_hash": _source_segment_pin_hash(item.model_dump(mode="json"))}
        for item in build_child_section_inputs(guidance_facts)
        if item.section_key not in source_keys
    ]
    result = await repository.create_generation_idempotently(
        owner_user_id=owner_user_id,
        child_profile_id=child_profile_id,
        parent_chart_id=source_generation.parent_chart_id,
        child_chart_version_id=source_generation.child_chart_version_id,
        questionnaire_session_id=source_generation.questionnaire_session_id,
        operation=ChildGenerationOperation.NARRATIVE_RETRY.value,
        idempotency_key=idempotency_key,
        source_report_id=source_report_id,
        operation_payload={
            "source_generation_id": str(source_generation.generation_id),
            "source_report_id": str(source_report.id),
            "source_report_version": source_report.version,
            "guidance_facts_id": str(facts_row.id),
            "guidance_contract_version": facts_row.contract_version,
            "guidance_input_hash": _guidance_facts_input_hash(facts_row),
            "failed_section_pins": failed_section_pins,
            "missing_section_pins": missing_section_pins,
            **({"scope": scope} if scope == "narrative_all" else {}),
        },
    )
    if result.created:
        current = now or datetime.now(UTC)
        result.generation.next_retry_at = current + timedelta(seconds=settings.CHILD_GENERATION_RETRY_BASE_SECONDS)
    await session.commit()
    return ChildGenerationAccepted(
        generation_id=result.generation.generation_id,
        status=result.generation.status,
        report_id=source_report_id,
        created=result.created,
        task_id=result.generation.celery_task_id,
    )


def _deterministic_report_payload(
    *,
    generation: models.ChildGeneration,
    guidance_facts: Any,
    parent_style: Any,
    child_needs: Any,
    interaction: Any,
) -> dict[str, Any]:
    return {
        "contract_version": "child_report_deterministic_v1",
        "status": ChildGenerationStatus.DETERMINISTIC_READY.value,
        "generation_id": str(generation.generation_id),
        "child_id": str(generation.child_profile_id),
        "age_snapshot_id": str(guidance_facts.age_snapshot_id),
        "core_report_version": guidance_facts.core_report_version,
        "parent_style": [
            {"dimension": row.dimension, "score": row.score, "confidence": row.confidence}
            for row in parent_style.scores
        ],
        "child_needs": [
            {"dimension": row.dimension, "score": row.score, "confidence": row.confidence} for row in child_needs.scores
        ],
        "interaction": [
            {
                "dimension": row.dimension,
                "score": row.score,
                "confidence": row.confidence,
                "pattern": row.pattern,
            }
            for row in interaction.scores
        ],
        "guidance_facts": guidance_facts.to_payload(),
    }


async def run_claimed_full_generation(
    session: AsyncSession,
    *,
    claim: ChildGenerationClaim,
    provider: ChildSegmentProvider,
    now: datetime | None = None,
) -> ChildGenerationRunResult:
    """Run deterministic publication first, then independently persisted sections."""

    def clock() -> datetime:
        return now if now is not None else datetime.now(UTC)

    lease_duration = timedelta(seconds=settings.CHILD_GENERATION_LEASE_SECONDS)
    repository = ChildRepository(session)
    generation = claim.generation
    generation_id = generation.generation_id
    provider_calls = 0

    async def checkpoint() -> None:
        heartbeat = await repository.heartbeat_generation(
            generation_id=generation.generation_id,
            claim_token=claim.claim_token,
            now=clock(),
            lease_duration=lease_duration,
        )
        if not heartbeat:
            raise RuntimeError("Child generation lease was lost")
        await session.commit()

    if generation.questionnaire_session_id is None:
        await repository.fail_claimed_generation(
            generation_id=generation.generation_id,
            claim_token=claim.claim_token,
            now=clock(),
            error_code="questionnaire_not_pinned",
        )
        await session.commit()
        return ChildGenerationRunResult(
            generation_id=generation.generation_id,
            status=ChildGenerationStatus.FAILED.value,
            report_id=None,
            provider_calls=0,
        )

    try:
        report_was_published = generation.report_id is not None
        if report_was_published:
            report = await session.scalar(
                select(models.ChildReport).where(
                    models.ChildReport.id == generation.report_id,
                    models.ChildReport.child_profile_id == generation.child_profile_id,
                    models.ChildReport.generation_id == generation.generation_id,
                )
            )
            if report is None or report.status != ChildGenerationStatus.DETERMINISTIC_READY.value:
                raise RuntimeError("Published deterministic report is unavailable")
            guidance_facts = await ChildGuidanceFactsRepository(session).load_domain_facts(
                owner_user_id=generation.owner_user_id,
                child_profile_id=generation.child_profile_id,
                generation_id=generation.generation_id,
                core_report_version=report.version,
            )
            report_id = report.id
        else:
            parent_style = await repository.create_parent_style_profile(
                owner_user_id=generation.owner_user_id,
                child_profile_id=generation.child_profile_id,
                generation_id=generation.generation_id,
            )
            await checkpoint()
            child_needs = await repository.create_child_need_profile(
                owner_user_id=generation.owner_user_id,
                child_profile_id=generation.child_profile_id,
                generation_id=generation.generation_id,
            )
            await checkpoint()
            interaction = await repository.create_interaction_profile(
                owner_user_id=generation.owner_user_id,
                child_profile_id=generation.child_profile_id,
                generation_id=generation.generation_id,
            )
            await checkpoint()
            await ChildContextResolutionRepository(session).create_or_load(
                owner_user_id=generation.owner_user_id,
                child_profile_id=generation.child_profile_id,
                generation_id=generation.generation_id,
                questionnaire_session_id=generation.questionnaire_session_id,
            )
            await checkpoint()
            report_version = await repository.allocate_report_version(child_profile_id=generation.child_profile_id)
            facts_repository = ChildGuidanceFactsRepository(session)
            guidance_facts = await facts_repository.load_domain_facts(
                owner_user_id=generation.owner_user_id,
                child_profile_id=generation.child_profile_id,
                generation_id=generation.generation_id,
                core_report_version=report_version,
            )
            questionnaire = await session.get(models.ChildQuestionnaireSession, generation.questionnaire_session_id)
            if questionnaire is None:
                raise RuntimeError("Pinned questionnaire disappeared")
            report_result = await repository.create_report_idempotently(
                owner_user_id=generation.owner_user_id,
                child_profile_id=generation.child_profile_id,
                generation_id=generation.generation_id,
                parent_chart_id=generation.parent_chart_id,
                child_chart_version_id=generation.child_chart_version_id,
                idempotency_key=f"child-generation:{generation.generation_id}",
                version=report_version,
                status=ChildGenerationStatus.DETERMINISTIC_READY.value,
                scoring_version=INTERACTION_SCORING_VERSION,
                reference_version=INTERACTION_REFERENCE_VERSION,
                questionnaire_version=questionnaire.questionnaire_version,
                prompt_version=CHILD_PROMPT_VERSION,
                report_payload=_deterministic_report_payload(
                    generation=generation,
                    guidance_facts=guidance_facts,
                    parent_style=parent_style,
                    child_needs=child_needs,
                    interaction=interaction,
                ),
                presentation_manifest={
                    "contract_version": "child_report_presentation_v1",
                    "section_order": list(SECTION_METADATA),
                    "age_snapshot_id": str(guidance_facts.age_snapshot_id),
                },
            )
            report_id = report_result.report.id

        if not report_was_published:
            await repository.transition_generation(
                generation_id=generation.generation_id,
                claim_token=claim.claim_token,
                expected_status=ChildGenerationStatus.CALCULATING_PAIR,
                target_status=ChildGenerationStatus.DETERMINISTIC_READY,
                now=clock(),
                report_id=report_id,
            )
            # This commit is the user-visible deterministic-ready publication boundary.
            await session.commit()

            await repository.transition_generation(
                generation_id=generation.generation_id,
                claim_token=claim.claim_token,
                expected_status=ChildGenerationStatus.DETERMINISTIC_READY,
                target_status=ChildGenerationStatus.GENERATING_SECTIONS,
                now=clock(),
            )
            await session.commit()

        existing = {
            row.section_key: row
            for row in await repository.list_segment_generations(
                child_profile_id=generation.child_profile_id,
                generation_id=generation.generation_id,
            )
        }
        provider_calls = 0
        for section_input in build_child_section_inputs(guidance_facts):
            previous = existing.get(section_input.section_key)
            if previous is not None and previous.status in {"ready", "not_applicable", "failed"}:
                continue
            if section_input.owned_facts:
                intent = build_child_segment_intent(
                    provider=provider,
                    section_input=section_input,
                    guidance_facts=guidance_facts,
                    lifecycle_token=claim.claim_token,
                )
                intent_result = await repository.claim_segment_intent(
                    row=intent,
                    claim_token=claim.claim_token,
                )
                await checkpoint()
                if intent_result != "claimed":
                    continue
                if not isinstance(provider, DisabledChildSegmentProvider):
                    provider_calls += 1
            row = await run_child_segment_generation(
                provider=provider,
                section_input=section_input,
                guidance_facts=guidance_facts,
            )
            if row.error_code == "child_narrative_provider_failure":
                await repository.mark_segment_retry_waiting(
                    generation_id=generation.generation_id,
                    section_key=section_input.section_key,
                    claim_token=claim.claim_token,
                    diagnostics=row.diagnostics,
                )
                await checkpoint()
                released = await repository.release_generation_for_retry(
                    generation_id=generation_id,
                    claim_token=claim.claim_token,
                    now=clock(),
                    retry_base_seconds=settings.CHILD_GENERATION_RETRY_BASE_SECONDS,
                    max_attempts=settings.CHILD_GENERATION_MAX_ATTEMPTS,
                    error_code="child_narrative_provider_failure",
                )
                if released.status == ChildGenerationStatus.NARRATIVE_FAILED.value:
                    await repository.finalize_segment_retry_exhausted(
                        generation_id=generation_id,
                        section_key=section_input.section_key,
                    )
                await session.commit()
                return ChildGenerationRunResult(
                    generation_id=generation_id,
                    status=released.status,
                    report_id=report_id,
                    provider_calls=provider_calls,
                )
            await repository.persist_terminal_segment(
                row=row,
                claim_token=claim.claim_token if section_input.owned_facts else None,
            )
            await checkpoint()

        segments = await repository.list_segment_generations(
            child_profile_id=generation.child_profile_id,
            generation_id=generation.generation_id,
        )
        assembled = assemble_child_report_payload(
            guidance_facts=guidance_facts,
            segment_rows=segments,
        )
        target = (
            ChildGenerationStatus.READY if assembled["status"] == "ready" else ChildGenerationStatus.NARRATIVE_FAILED
        )
        await repository.create_report_assembly_idempotently(
            child_profile_id=generation.child_profile_id,
            generation_id=generation.generation_id,
            source_generation_id=generation.generation_id,
            report_id=report_id,
            status=target.value,
            contract_version=str(assembled["contract_version"]),
            payload=assembled,
        )
        await repository.transition_generation(
            generation_id=generation.generation_id,
            claim_token=claim.claim_token,
            expected_status=ChildGenerationStatus.GENERATING_SECTIONS,
            target_status=target,
            now=clock(),
            error_code=None if target is ChildGenerationStatus.READY else "narrative_generation_failed",
        )
        await session.commit()
        return ChildGenerationRunResult(
            generation_id=generation.generation_id,
            status=target.value,
            report_id=report_id,
            provider_calls=provider_calls,
        )
    except Exception:
        await session.rollback()
        released = await repository.release_generation_for_retry(
            generation_id=generation_id,
            claim_token=claim.claim_token,
            now=clock(),
            retry_base_seconds=settings.CHILD_GENERATION_RETRY_BASE_SECONDS,
            max_attempts=settings.CHILD_GENERATION_MAX_ATTEMPTS,
            error_code="child_generation_transient_failure",
        )
        await session.commit()
        return ChildGenerationRunResult(
            generation_id=generation_id,
            status=released.status,
            report_id=released.report_id,
            provider_calls=provider_calls,
        )


async def run_claimed_narrative_retry(
    session: AsyncSession,
    *,
    claim: ChildGenerationClaim,
    provider: ChildSegmentProvider,
    now: datetime | None = None,
) -> ChildGenerationRunResult:
    """Retry only failed narrative sections against pinned deterministic artifacts."""

    def clock() -> datetime:
        return now if now is not None else datetime.now(UTC)

    generation = claim.generation
    generation_id = generation.generation_id
    generation_source_report_id = generation.source_report_id
    provider_calls = 0
    repository = ChildRepository(session)
    lease_duration = timedelta(seconds=settings.CHILD_GENERATION_LEASE_SECONDS)

    async def checkpoint() -> None:
        heartbeat = await repository.heartbeat_generation(
            generation_id=generation_id,
            claim_token=claim.claim_token,
            now=clock(),
            lease_duration=lease_duration,
        )
        if not heartbeat:
            raise RuntimeError("Child generation lease was lost")
        await session.commit()

    try:
        if generation.operation != ChildGenerationOperation.NARRATIVE_RETRY.value:
            raise RuntimeError("Narrative retry operation is invalid")
        payload = generation.operation_payload
        source_generation_id = UUID(str(payload["source_generation_id"]))
        source_report_id = UUID(str(payload["source_report_id"]))
        source_report_version = payload["source_report_version"]
        guidance_facts_id = UUID(str(payload["guidance_facts_id"]))
        failed_section_pins = payload.get("failed_section_pins")
        retry_scope = payload.get("scope", "failed_sections")
        if retry_scope not in {"failed_sections", "narrative_all"}:
            raise RuntimeError("Pinned narrative scope is invalid")
        if (
            generation.source_report_id != source_report_id
            or type(source_report_version) is not int
            or not isinstance(payload.get("guidance_contract_version"), str)
            or not isinstance(payload.get("guidance_input_hash"), str)
            or not isinstance(failed_section_pins, list)
            or not failed_section_pins
            or not all(isinstance(pin, dict) for pin in failed_section_pins)
        ):
            raise RuntimeError("Narrative retry pins are invalid")
        report = await session.scalar(
            select(models.ChildReport).where(
                models.ChildReport.id == source_report_id,
                models.ChildReport.child_profile_id == generation.child_profile_id,
                models.ChildReport.generation_id == source_generation_id,
                models.ChildReport.version == source_report_version,
            )
        )
        facts_row = await session.scalar(
            select(models.ChildGuidanceFacts).where(
                models.ChildGuidanceFacts.id == guidance_facts_id,
                models.ChildGuidanceFacts.child_profile_id == generation.child_profile_id,
                models.ChildGuidanceFacts.generation_id == source_generation_id,
                models.ChildGuidanceFacts.core_report_version == source_report_version,
                models.ChildGuidanceFacts.contract_version == payload["guidance_contract_version"],
            )
        )
        if report is None or facts_row is None:
            raise RuntimeError("Pinned narrative source lineage is unavailable")
        if _guidance_facts_input_hash(facts_row) != payload["guidance_input_hash"]:
            raise RuntimeError("Pinned narrative guidance facts are corrupt")
        unknown_retry = await session.scalar(
            select(models.ChildSegmentGeneration.id)
            .join(
                models.ChildGeneration,
                models.ChildGeneration.generation_id == models.ChildSegmentGeneration.generation_id,
            )
            .where(
                models.ChildGeneration.source_report_id == source_report_id,
                models.ChildGeneration.operation == ChildGenerationOperation.NARRATIVE_RETRY.value,
                models.ChildGeneration.generation_id != generation_id,
                models.ChildSegmentGeneration.error_code == "child_narrative_provider_outcome_unknown",
            )
            .limit(1)
        )
        if unknown_retry is not None:
            raise RuntimeError("Another narrative retry has an unknown provider outcome")
        guidance_facts = await ChildGuidanceFactsRepository(session).load_domain_facts(
            owner_user_id=generation.owner_user_id,
            child_profile_id=generation.child_profile_id,
            generation_id=source_generation_id,
            core_report_version=source_report_version,
        )
        source_segments = await repository.list_segment_generations(
            child_profile_id=generation.child_profile_id,
            generation_id=source_generation_id,
        )
        source_by_id = {str(row.id): row for row in source_segments}
        all_source_by_key = {row.section_key: row for row in source_segments}
        pinned_source_by_key: dict[str, models.ChildSegmentGeneration] = {}
        for raw_pin in failed_section_pins:
            pin = cast(dict[str, Any], raw_pin)
            pin_hash = pin.get("pin_hash")
            pinned_values = {key: value for key, value in pin.items() if key != "pin_hash"}
            if not isinstance(pin_hash, str) or _source_segment_pin_hash(pinned_values) != pin_hash:
                raise RuntimeError("Pinned narrative source segment hash is corrupt")
            source_row = source_by_id.get(str(pin.get("id")))
            if source_row is None or _source_segment_pin(source_row) != pinned_values:
                raise RuntimeError("Pinned narrative source segment is unavailable or changed")
            section_key = pin.get("section_key")
            allowed_pin_statuses = (
                {"failed", "ready", "not_applicable"} if retry_scope == "narrative_all" else {"failed"}
            )
            if (
                not isinstance(section_key, str)
                or section_key in pinned_source_by_key
                or source_row.status not in allowed_pin_statuses
            ):
                raise RuntimeError("Pinned narrative retry scope is invalid")
            pinned_source_by_key[section_key] = source_row
        if set(pinned_source_by_key) != {
            row.section_key for row in source_segments if retry_scope == "narrative_all" or row.status == "failed"
        }:
            raise RuntimeError("Pinned narrative retry scope is incomplete")
        section_inputs = build_child_section_inputs(guidance_facts)
        missing_section_pins = [
            {"section_key": item.section_key, "input_hash": _source_segment_pin_hash(item.model_dump(mode="json"))}
            for item in section_inputs
            if item.section_key not in all_source_by_key
        ]
        if payload.get("missing_section_pins", []) != missing_section_pins:
            raise RuntimeError("Pinned missing narrative retry scope is corrupt")
        missing_keys = {pin["section_key"] for pin in missing_section_pins}
        retry_existing = {
            row.section_key: row
            for row in await repository.list_segment_generations(
                child_profile_id=generation.child_profile_id,
                generation_id=generation_id,
            )
        }
        provider_calls = 0
        retry_rows: dict[str, models.ChildSegmentGeneration] = dict(retry_existing)
        for section_input in section_inputs:
            source_row = pinned_source_by_key.get(section_input.section_key)
            if source_row is None and section_input.section_key not in missing_keys:
                continue
            existing = retry_existing.get(section_input.section_key)
            if existing is not None and existing.status in {"ready", "failed", "not_applicable"}:
                continue
            if source_row is not None and source_row.error_code == "child_narrative_provider_outcome_unknown":
                fenced = models.ChildSegmentGeneration(
                    child_profile_id=generation.child_profile_id,
                    generation_id=generation_id,
                    section_key=source_row.section_key,
                    status="failed",
                    prompt_version=source_row.prompt_version,
                    model=source_row.model,
                    content=None,
                    evidence_refs=[],
                    error_code=source_row.error_code,
                    lifecycle_token=claim.claim_token,
                    diagnostics=dict(source_row.diagnostics),
                )
                retry_rows[section_input.section_key] = await repository.persist_terminal_segment(
                    row=fenced,
                    claim_token=None,
                )
                await checkpoint()
                continue
            if section_input.owned_facts:
                intent = build_child_segment_intent(
                    provider=provider,
                    section_input=section_input,
                    guidance_facts=guidance_facts,
                    lifecycle_token=claim.claim_token,
                    artifact_generation_id=generation_id,
                )
                intent_result = await repository.claim_segment_intent(
                    row=intent,
                    claim_token=claim.claim_token,
                )
                await checkpoint()
                if intent_result != "claimed":
                    continue
                if not isinstance(provider, DisabledChildSegmentProvider):
                    provider_calls += 1
            row = await run_child_segment_generation(
                provider=provider,
                section_input=section_input,
                guidance_facts=guidance_facts,
                artifact_generation_id=generation_id,
            )
            if row.error_code == "child_narrative_provider_failure":
                await repository.mark_segment_retry_waiting(
                    generation_id=generation_id,
                    section_key=section_input.section_key,
                    claim_token=claim.claim_token,
                    diagnostics=row.diagnostics,
                )
                await checkpoint()
                released = await repository.release_generation_for_retry(
                    generation_id=generation_id,
                    claim_token=claim.claim_token,
                    now=clock(),
                    retry_base_seconds=settings.CHILD_GENERATION_RETRY_BASE_SECONDS,
                    max_attempts=settings.CHILD_GENERATION_MAX_ATTEMPTS,
                    error_code="child_narrative_provider_failure",
                )
                if released.status == ChildGenerationStatus.NARRATIVE_FAILED.value:
                    await repository.finalize_segment_retry_exhausted(
                        generation_id=generation_id,
                        section_key=section_input.section_key,
                    )
                await session.commit()
                return ChildGenerationRunResult(
                    generation_id=generation_id,
                    status=released.status,
                    report_id=source_report_id,
                    provider_calls=provider_calls,
                )
            retry_rows[section_input.section_key] = await repository.persist_terminal_segment(
                row=row,
                claim_token=claim.claim_token if section_input.owned_facts else None,
            )
            await checkpoint()
        # Assemble from the committed rows, not ORM identities retained across
        # retry-intent upserts (which can still carry the pre-update status).
        retry_rows = {
            row.section_key: row
            for row in await repository.list_segment_generations(
                child_profile_id=generation.child_profile_id,
                generation_id=generation_id,
            )
        }
        merged = dict(all_source_by_key)
        merged.update(retry_rows)
        assembled = assemble_child_report_payload(
            guidance_facts=guidance_facts,
            segment_rows=tuple(merged.values()),
            artifact_generation_id=generation_id,
        )
        target = (
            ChildGenerationStatus.READY if assembled["status"] == "ready" else ChildGenerationStatus.NARRATIVE_FAILED
        )
        await repository.create_report_assembly_idempotently(
            child_profile_id=generation.child_profile_id,
            generation_id=generation_id,
            source_generation_id=source_generation_id,
            report_id=source_report_id,
            status=target.value,
            contract_version=str(assembled["contract_version"]),
            payload=assembled,
        )
        await repository.transition_generation(
            generation_id=generation_id,
            claim_token=claim.claim_token,
            expected_status=ChildGenerationStatus.GENERATING_SECTIONS,
            target_status=target,
            now=clock(),
            report_id=source_report_id,
            error_code=None if target is ChildGenerationStatus.READY else "narrative_generation_failed",
        )
        await session.commit()
        return ChildGenerationRunResult(
            generation_id=generation_id,
            status=target.value,
            report_id=source_report_id,
            provider_calls=provider_calls,
        )
    except Exception:
        await session.rollback()
        released = await repository.release_generation_for_retry(
            generation_id=generation_id,
            claim_token=claim.claim_token,
            now=clock(),
            retry_base_seconds=settings.CHILD_GENERATION_RETRY_BASE_SECONDS,
            max_attempts=settings.CHILD_GENERATION_MAX_ATTEMPTS,
            error_code="child_narrative_retry_transient_failure",
        )
        await session.commit()
        return ChildGenerationRunResult(
            generation_id=generation_id,
            status=released.status,
            report_id=generation_source_report_id,
            provider_calls=provider_calls,
        )


async def run_claimed_age_update(
    session: AsyncSession,
    *,
    claim: ChildGenerationClaim,
    now: datetime | None = None,
) -> ChildGenerationRunResult:
    """Persist only the append-only age artifact and close its separate lifecycle."""

    current = now or datetime.now(UTC)
    generation = claim.generation
    generation_id = generation.generation_id
    source_report_id = generation.source_report_id
    repository = ChildRepository(session)
    try:
        if generation.operation != ChildGenerationOperation.AGE_UPDATE.value or generation.source_report_id is None:
            raise RuntimeError("Age update generation target is invalid")
        guidance_rules_version = generation.operation_payload.get("guidance_rules_version")
        guidance_input_hash = generation.operation_payload.get("guidance_input_hash")
        age_snapshot_id_raw = generation.operation_payload.get("age_snapshot_id")
        age_input_hash = generation.operation_payload.get("age_input_hash")
        age_rules_version = generation.operation_payload.get("age_rules_version")
        source_generation_id_raw = generation.operation_payload.get("source_generation_id")
        source_report_id_raw = generation.operation_payload.get("source_report_id")
        payload = generation.operation_payload.get("payload")
        if not all(
            isinstance(value, str)
            for value in (
                guidance_rules_version,
                guidance_input_hash,
                age_snapshot_id_raw,
                age_input_hash,
                age_rules_version,
                source_generation_id_raw,
                source_report_id_raw,
            )
        ) or not isinstance(payload, dict):
            raise RuntimeError("Age update operation payload is invalid")
        guidance_rules_version = cast(str, guidance_rules_version)
        guidance_input_hash = cast(str, guidance_input_hash)
        age_snapshot_id_raw = cast(str, age_snapshot_id_raw)
        age_input_hash = cast(str, age_input_hash)
        age_rules_version = cast(str, age_rules_version)
        source_generation_id_raw = cast(str, source_generation_id_raw)
        source_report_id_raw = cast(str, source_report_id_raw)
        age_snapshot_id = UUID(age_snapshot_id_raw)
        source_generation_id = UUID(source_generation_id_raw)
        source_report_id = UUID(source_report_id_raw)
        if source_report_id != generation.source_report_id:
            raise RuntimeError("Pinned age source report is corrupt")
        source_report = await session.scalar(
            select(models.ChildReport).where(
                models.ChildReport.id == source_report_id,
                models.ChildReport.child_profile_id == generation.child_profile_id,
                models.ChildReport.generation_id == source_generation_id,
            )
        )
        if source_report is None:
            raise RuntimeError("Pinned age source lineage is unavailable")
        snapshot = await session.scalar(
            select(models.ChildAgeSnapshot).where(
                models.ChildAgeSnapshot.id == age_snapshot_id,
                models.ChildAgeSnapshot.child_profile_id == generation.child_profile_id,
                models.ChildAgeSnapshot.input_hash == age_input_hash,
                models.ChildAgeSnapshot.age_rules_version == age_rules_version,
            )
        )
        if snapshot is None:
            raise RuntimeError("Pinned age snapshot is unavailable")
        expected_guidance_input_hash = hashlib.sha256(
            json.dumps(
                {
                    "age_snapshot_id": str(age_snapshot_id),
                    "age_input_hash": age_input_hash,
                    "age_rules_version": age_rules_version,
                    "guidance_rules_version": guidance_rules_version,
                    "payload": payload,
                    "source_generation_id": str(source_generation_id),
                    "source_report_id": str(source_report_id),
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        if guidance_input_hash != expected_guidance_input_hash:
            raise RuntimeError("Pinned age guidance input is corrupt")
        await repository.create_age_update_idempotently(
            owner_user_id=generation.owner_user_id,
            child_profile_id=generation.child_profile_id,
            report_id=generation.source_report_id,
            idempotency_key=f"age-generation:{generation.generation_id}",
            guidance_rules_version=guidance_rules_version,
            payload=payload,
            now=current,
            age_rules_version=age_rules_version,
            pinned_age_snapshot_id=age_snapshot_id,
        )
        await repository.transition_generation(
            generation_id=generation.generation_id,
            claim_token=claim.claim_token,
            expected_status=ChildGenerationStatus.AGE_UPDATE_RUNNING,
            target_status=ChildGenerationStatus.AGE_UPDATE_READY,
            now=current,
        )
        await session.commit()
        return ChildGenerationRunResult(
            generation_id=generation.generation_id,
            status=ChildGenerationStatus.AGE_UPDATE_READY.value,
            report_id=generation.source_report_id,
            provider_calls=0,
        )
    except Exception:
        await session.rollback()
        released = await repository.release_generation_for_retry(
            generation_id=generation_id,
            claim_token=claim.claim_token,
            now=current,
            retry_base_seconds=settings.CHILD_GENERATION_RETRY_BASE_SECONDS,
            max_attempts=settings.CHILD_GENERATION_MAX_ATTEMPTS,
            error_code="child_age_update_transient_failure",
        )
        await session.commit()
        return ChildGenerationRunResult(
            generation_id=generation_id,
            status=released.status,
            report_id=source_report_id,
            provider_calls=0,
        )


async def run_age_update(
    session: AsyncSession,
    *,
    owner_user_id: UUID,
    child_profile_id: UUID,
    report_id: UUID,
    idempotency_key: str,
    guidance_rules_version: str,
    payload: dict[str, Any],
    now: datetime | None = None,
) -> Any:
    """Append only age guidance; never invoke pair scoring or narrative generation."""

    result = await ChildRepository(session).create_age_update_idempotently(
        owner_user_id=owner_user_id,
        child_profile_id=child_profile_id,
        report_id=report_id,
        idempotency_key=idempotency_key,
        guidance_rules_version=guidance_rules_version,
        payload=payload,
        now=now,
    )
    await session.commit()
    return result


async def list_queued_generation_ids(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    limit: int = 100,
) -> tuple[UUID, ...]:
    current = now or datetime.now(UTC)
    rows = await session.scalars(
        select(models.ChildGeneration.generation_id)
        .where(
            models.ChildGeneration.status.in_([status.value for status in CLAIMABLE_STATUSES]),
            (models.ChildGeneration.next_retry_at.is_(None)) | (models.ChildGeneration.next_retry_at <= current),
            (models.ChildGeneration.celery_task_id.is_(None))
            | (models.ChildGeneration.dispatch_expires_at.is_(None))
            | (models.ChildGeneration.dispatch_expires_at < current),
        )
        .order_by(models.ChildGeneration.created_at, models.ChildGeneration.id)
        .limit(limit)
    )
    return tuple(rows.all())
