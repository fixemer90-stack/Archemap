"""Durable deterministic-first Career report generation task."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, cast

import structlog
from sqlalchemy import select
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
from app.modules.career.profile_resolver import build_resolution_row, resolve_career_profile
from app.modules.career.questionnaire import CareerQuestionnaireCompleted
from app.modules.career.repository import CareerRepository
from app.modules.career.role_matching import build_role_match_rows, match_roles
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
        try:
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
            assembled = assemble_career_report_row(report=report, segment_rows=list(segment_rows))
            report.status = assembled.status
            report.narrative_payload = assembled.narrative_payload
            report.assembled_payload = assembled.assembled_payload
            generation.status = assembled.status
            generation.diagnostics = {"stage": "complete", "report_status": assembled.status}
            await db.commit()
            return {
                "generation_id": str(generation.generation_id),
                "report_id": str(report.id),
                "status": report.status,
            }
        except Exception as exc:
            await db.rollback()
            generation = await _load_generation(db, generation_id)
            if generation is not None:
                generation.status = "failed"
                generation.diagnostics = {"stage": "failed", "error": type(exc).__name__}
                await db.commit()
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
