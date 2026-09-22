"""Durable deterministic-first Career report generation task."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any, cast

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.celery_async import run_async_in_worker
from app.infrastructure.database import async_session_factory
from app.modules.astrotype_v2.models import NatalFact
from app.modules.career import models
from app.modules.career.archetype_engine import build_archetype_rows, match_archetypes
from app.modules.career.career_paths import build_career_path_rows, build_career_paths
from app.modules.career.dimension_engine import score_career_dimensions
from app.modules.career.dimension_persistence import build_dimension_rows
from app.modules.career.environment_engine import build_environment_rows, score_work_environment
from app.modules.career.interpretation_facts import (
    CareerInterpretationFacts,
    build_interpretation_fact_rows,
    build_interpretation_facts,
)
from app.modules.career.narrative import (
    MockCareerSegmentProvider,
    StructuredCareerSegmentProviderAdapter,
    assemble_career_report_row,
    build_career_section_inputs,
    build_deterministic_career_report_row,
    run_career_segment_generation,
)
from app.modules.career.observability import bind_career_context, career_telemetry, safe_error_code
from app.modules.career.profile_resolver import build_resolution_row, resolve_career_profile
from app.modules.career.questionnaire import CareerQuestionnaireCompleted
from app.modules.career.repository import CareerRepository
from app.modules.career.role_matching import ROLE_CATALOG_VERSION, build_role_match_rows, match_roles
from app.modules.llm.provider import get_llm_provider
from workers.celery_app import app

logger = structlog.get_logger()


@app.task(  # type: ignore[untyped-decorator]
    name="career.generate_report",
    bind=True,
    max_retries=settings.LLM_MAX_RETRIES,
    default_retry_delay=30,
    soft_time_limit=max(settings.LLM_TIMEOUT_SECONDS * 4, 600),
    time_limit=max(settings.LLM_TIMEOUT_SECONDS * 4 + 120, 720),
)
def generate_career_report(
    self: object,
    *,
    generation_id: str,
    section_keys: list[str] | None = None,
) -> dict[str, Any]:
    del self
    return run_async_in_worker(
        _generate_career_report_async(
            generation_id=uuid.UUID(generation_id),
            section_keys=section_keys or [],
        )
    )


@app.task(name="career.monitor_pipeline")  # type: ignore[untyped-decorator]
def monitor_career_pipeline() -> dict[str, Any]:
    return run_async_in_worker(_monitor_career_pipeline_async())


async def _monitor_career_pipeline_async() -> dict[str, Any]:
    now = datetime.now(UTC)
    stuck_cutoff = now - timedelta(minutes=settings.CAREER_STUCK_AFTER_MINUTES)
    validator_cutoff = now - timedelta(minutes=settings.CAREER_MONITOR_WINDOW_MINUTES)
    active_stage_by_status = {
        "queued": "deterministic",
        "calculating_dimensions": "deterministic",
        "deterministic_ready": "narrative",
        "generating_sections": "narrative",
    }
    async with async_session_factory() as db:
        stuck_result = await db.execute(
            select(models.CareerGeneration.status, func.count())
            .where(
                models.CareerGeneration.status.in_(tuple(active_stage_by_status)),
                models.CareerGeneration.updated_at < stuck_cutoff,
            )
            .group_by(models.CareerGeneration.status)
        )
        stuck_by_stage = {"deterministic": 0, "narrative": 0}
        for status_name, count in stuck_result.all():
            stuck_by_stage[active_stage_by_status[str(status_name)]] += int(count)
        validator_result = await db.execute(
            select(func.count())
            .select_from(models.CareerSegmentGeneration)
            .where(
                models.CareerSegmentGeneration.error == "career_validation_failure",
                models.CareerSegmentGeneration.updated_at >= validator_cutoff,
            )
        )
        validator_failures = int(validator_result.scalar_one())

    for stage_name, count in stuck_by_stage.items():
        if count:
            career_telemetry.record(
                stage=stage_name,
                outcome="stuck",
                operation="scan",
                error_code="career_stuck_generation",
                amount=count,
            )
    alerts = build_career_monitor_alerts(
        stuck_by_stage=stuck_by_stage,
        validator_failures=validator_failures,
        validator_failure_threshold=settings.CAREER_VALIDATOR_ALERT_THRESHOLD,
    )
    for alert in alerts:
        logger.warning("career_pipeline_alert", alert=alert)
    return {
        "stuck_by_stage": stuck_by_stage,
        "validator_failures": validator_failures,
        "alerts": list(alerts),
    }


async def _generate_career_report_async(
    *,
    generation_id: uuid.UUID,
    section_keys: list[str],
) -> dict[str, Any]:
    async with async_session_factory() as db:
        repository = CareerRepository(db)
        generation = await _load_generation(db, generation_id)
        if generation is None:
            raise ValueError("Career generation not found")
        stage = "deterministic"
        stage_started = perf_counter()
        event_logger = bind_career_context(
            generation_id=str(generation.generation_id),
            report_id=str(generation.report_id) if generation.report_id else None,
            user_id=str(generation.user_id),
        )
        try:
            event_logger.info("career_generation_started", operation=generation.operation)
            generation.status = "calculating_dimensions"
            generation.diagnostics = {"stage": "deterministic"}
            await db.commit()

            if generation.operation == "regenerate":
                if generation.source_report_id is None:
                    raise ValueError("Regeneration source report is missing")
                source = await repository.get_report_for_user(generation.source_report_id, generation.user_id)
                if source is None:
                    raise ValueError("Regeneration source report not found")
                report = build_regeneration_report_row(
                    source=source,
                    generation_id=generation.generation_id,
                    idempotency_key=generation.idempotency_key,
                )
                facts = CareerInterpretationFacts.model_validate(report.deterministic_payload)
            else:
                profile = await repository.get_profile_for_user(generation.career_profile_id, generation.user_id)
                if profile is None:
                    raise ValueError("Career profile not found")
                questionnaire = await repository.get_questionnaire_session(
                    career_profile_id=profile.id,
                    questionnaire_version=profile.questionnaire_version,
                )
                if questionnaire is None or questionnaire.status != "completed":
                    raise ValueError("Questionnaire is not completed")
                answer_rows = await repository.list_questionnaire_answers(questionnaire.id)
                answers = CareerQuestionnaireCompleted.model_validate(
                    {row.question_key: row.answer.get("value") for row in answer_rows}
                )
                natal_facts_result = await db.execute(
                    select(NatalFact).where(NatalFact.chart_id == profile.chart_id).order_by(NatalFact.fact_key)
                )
                natal_facts = list(natal_facts_result.scalars().all())
                if not natal_facts:
                    raise ValueError("Persisted v2 natal facts are missing")
                dimensions = list(score_career_dimensions(natal_facts))
                resolution = resolve_career_profile(dimensions=dimensions, answers=answers)
                archetypes = match_archetypes(dimensions=dimensions, resolution=resolution)
                environment = score_work_environment(dimensions=dimensions, resolution=resolution)
                role_matches = match_roles(
                    dimensions=dimensions,
                    environment=environment,
                    resolution=resolution,
                )
                career_paths = build_career_paths(matches=role_matches, resolution=resolution)
                facts = build_interpretation_facts(
                    profile_id=profile.id,
                    chart_id=profile.chart_id,
                    dimensions=dimensions,
                    archetypes=archetypes,
                    environment=environment,
                    resolution=resolution,
                    role_matches=role_matches,
                    career_paths=career_paths,
                )
                latest = await repository.get_latest_report(profile.id)
                report = build_deterministic_career_report_row(
                    facts=facts,
                    generation_id=generation.generation_id,
                    idempotency_key=generation.idempotency_key,
                    version=(latest.version + 1 if latest is not None else 1),
                )
                dimension_rows, evidence_rows = build_dimension_rows(
                    career_profile_id=profile.id,
                    chart_id=profile.chart_id,
                    results=dimensions,
                )
                archetype_rows = build_archetype_rows(
                    career_profile_id=profile.id,
                    chart_id=profile.chart_id,
                    results=archetypes,
                )
                environment_rows = build_environment_rows(
                    career_profile_id=profile.id,
                    chart_id=profile.chart_id,
                    result=environment,
                )
                role_rows = build_role_match_rows(
                    career_profile_id=profile.id,
                    chart_id=profile.chart_id,
                    matches=role_matches,
                )
                path_rows = build_career_path_rows(
                    career_profile_id=profile.id,
                    chart_id=profile.chart_id,
                    role_rows=role_rows,
                    paths=career_paths,
                )
                await repository.add_many(
                    [
                        *dimension_rows,
                        *evidence_rows,
                        build_resolution_row(
                            career_profile_id=profile.id,
                            chart_id=profile.chart_id,
                            resolution=resolution,
                        ),
                        *archetype_rows,
                        *environment_rows,
                        *role_rows,
                        *path_rows,
                        *build_interpretation_fact_rows(facts),
                    ]
                )

            await repository.add(report)
            await repository.flush()
            generation.report_id = report.id
            generation.status = "deterministic_ready"
            generation.diagnostics = {"stage": "deterministic_ready"}
            await db.commit()
            career_telemetry.record(
                stage="deterministic",
                outcome="ready",
                duration_seconds=perf_counter() - stage_started,
                operation=generation.operation,
            )
            career_telemetry.record(
                stage="deterministic",
                outcome="version_observed",
                operation=generation.operation,
                scoring_version=report.scoring_version,
                catalog_version=ROLE_CATALOG_VERSION,
            )
            if generation.operation == "regenerate":
                career_telemetry.record(stage="narrative", outcome="retried", operation="regenerate")
            stage = "narrative"
            stage_started = perf_counter()

            inputs = build_career_section_inputs(facts)
            if section_keys:
                requested = set(section_keys)
                unknown = requested - {item.section_key for item in inputs}
                if unknown:
                    raise ValueError(f"Unknown Career section keys: {sorted(unknown)}")
                inputs = [item for item in inputs if item.section_key in requested]
            generation.status = "generating_sections"
            generation.diagnostics = {"stage": "narrative", "section_keys": [item.section_key for item in inputs]}
            await db.commit()

            provider = _career_provider()
            segment_rows = await asyncio.gather(
                *(
                    run_career_segment_generation(
                        provider=provider,
                        section_input=section_input,
                        career_profile_id=report.career_profile_id,
                        chart_id=report.chart_id,
                        generation_id=report.generation_id,
                    )
                    for section_input in inputs
                )
            )
            await repository.add_many(segment_rows)
            for segment in segment_rows:
                career_telemetry.record(
                    stage="narrative",
                    outcome="ready" if segment.status == "ready" else "failed",
                    operation=generation.operation,
                    section_key=segment.section_key,
                )
            assembled = assemble_career_report_row(report=report, segment_rows=list(segment_rows))
            report.status = assembled.status
            report.narrative_payload = assembled.narrative_payload
            report.assembled_payload = assembled.assembled_payload
            generation.status = assembled.status
            generation.diagnostics = {"stage": "complete", "report_status": assembled.status}
            await db.commit()
            career_telemetry.record(
                stage="narrative",
                outcome="ready" if assembled.status == "ready" else "partial_failure",
                duration_seconds=perf_counter() - stage_started,
                operation=generation.operation,
            )
            event_logger.info(
                "career_generation_completed",
                report_id=str(report.id),
                status=report.status,
                scoring_version=report.scoring_version,
                prompt_version=report.prompt_version,
                model_version=settings.LLM_MODEL,
            )
            return {
                "generation_id": str(generation.generation_id),
                "report_id": str(report.id),
                "status": report.status,
            }
        except Exception as exc:
            await db.rollback()
            generation = await _load_generation(db, generation_id)
            if generation is not None:
                generation.status = failure_status_for_generation(report_id=generation.report_id)
                generation.diagnostics = {"stage": "failed", "error": type(exc).__name__}
                if generation.report_id is not None:
                    failed_report = await repository.get_report_for_user(
                        generation.report_id,
                        generation.user_id,
                    )
                    if failed_report is not None:
                        failed_report.status = "narrative_failed"
                await db.commit()
                career_telemetry.record(
                    stage=stage,
                    outcome="failed",
                    duration_seconds=perf_counter() - stage_started,
                    operation=generation.operation,
                    error_code=safe_error_code(exc, stage=stage),
                )
            logger.exception("career_generation_failed", generation_id=str(generation_id))
            raise


async def _load_generation(
    db: AsyncSession,
    generation_id: uuid.UUID,
) -> models.CareerGeneration | None:
    result = await db.execute(
        select(models.CareerGeneration).where(models.CareerGeneration.generation_id == generation_id)
    )
    return result.scalar_one_or_none()


def failure_status_for_generation(*, report_id: uuid.UUID | None) -> str:
    """Keep committed deterministic artifacts readable after narrative failure."""

    return "narrative_failed" if report_id is not None else "failed"


def build_career_monitor_alerts(
    *,
    stuck_by_stage: dict[str, int],
    validator_failures: int,
    validator_failure_threshold: int,
) -> tuple[str, ...]:
    alerts = [
        f"career_stuck_generation:{stage}:{stuck_by_stage[stage]}"
        for stage in ("deterministic", "narrative")
        if stuck_by_stage.get(stage, 0) > 0
    ]
    if validator_failures >= validator_failure_threshold:
        alerts.append(f"career_validator_failure_spike:{validator_failures}")
    return tuple(alerts)


def build_regeneration_report_row(
    *,
    source: models.CareerReport,
    generation_id: uuid.UUID,
    idempotency_key: str,
) -> models.CareerReport:
    """Create a new narrative attempt without mutating deterministic artifacts."""

    return models.CareerReport(
        career_profile_id=source.career_profile_id,
        chart_id=source.chart_id,
        generation_id=generation_id,
        idempotency_key=idempotency_key,
        version=source.version + 1,
        status="deterministic_ready",
        scoring_version=source.scoring_version,
        reference_version=source.reference_version,
        questionnaire_version=source.questionnaire_version,
        prompt_version=source.prompt_version,
        deterministic_payload=dict(source.deterministic_payload),
        narrative_payload={"sections": [], "section_order": source.narrative_payload.get("section_order", [])},
        assembled_payload={
            **source.assembled_payload,
            "status": "deterministic_ready",
            "regenerated_from": str(source.id),
        },
    )


def _career_provider() -> Any:
    if settings.LLM_PROVIDER == "mock":
        return MockCareerSegmentProvider()
    provider = get_llm_provider()
    return StructuredCareerSegmentProviderAdapter(
        provider=cast(Any, provider),
        provider_name=settings.LLM_PROVIDER,
        model_name=settings.LLM_MODEL,
    )
