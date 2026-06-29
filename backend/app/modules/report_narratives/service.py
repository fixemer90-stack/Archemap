# ruff: noqa: RUF001
"""Narrative generation orchestration and storage helpers."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from app.config import Settings, settings
from app.core.exceptions import NotFoundError
from app.modules.llm.exceptions import (
    LLMDisabledError,
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
    LLMTimeoutError,
)
from app.modules.llm.provider import LLMProvider, get_llm_provider
from app.modules.report_narratives.assembler import assemble_self_narrative
from app.modules.report_narratives.hash import compute_input_hash
from app.modules.report_narratives.input_builder import build_narrative_input
from app.modules.report_narratives.models import ReportNarrative
from app.modules.report_narratives.postprocess import harden_self_narrative
from app.modules.report_narratives.prompts import (
    SELF_STORY_PROMPT_VERSION,
    build_self_story_prompt,
    build_stage_prompt,
)
from app.modules.report_narratives.schemas import (
    AssemblyCheck,
    DeepNatalSynthesis,
    DevelopmentSectionOutput,
    EmotionalSectionOutput,
    HouseScenariosSectionOutput,
    IdentitySectionOutput,
    NarrativeInput,
    NarrativePlan,
    NarrativeStageArtifact,
    NarrativeStageId,
    NarrativeStageProgress,
    RelationshipSectionOutput,
    SelfNarrative,
)
from app.modules.report_narratives.validators import (
    choose_narrative_recovery_action,
    validate_assembled_self_narrative,
    validate_self_narrative,
)
from app.modules.reports.models import Report

logger = structlog.get_logger()

_STAGED_SELF_PIPELINE_PROMPT_VERSION = "self_staged_v1"
_STAGED_INVALID_RESPONSE_MAX_ATTEMPTS = 3


class ReportNarrativeService:
    """Generate, validate, cache, and persist structured narratives."""

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: LLMProvider | None = None,
        app_settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.app_settings = app_settings or settings
        self.llm_provider = llm_provider or get_llm_provider(self.app_settings)

    async def generate_for_report(self, report_id: UUID, *, force: bool = False) -> ReportNarrative:
        """Generate a narrative layer for a deterministic report."""
        report = await self._get_report(report_id)
        try:
            narrative_input = build_narrative_input(report)
            input_hash = compute_input_hash(narrative_input)
        except Exception as exc:
            logger.error(
                "report_narrative_invalid_input",
                report_id=str(report_id),
                product=report.product,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            raise
        model_name = getattr(self.llm_provider, "model_name", self.app_settings.LLM_MODEL)
        prompt_version = self._resolve_prompt_version(report, narrative_input)

        if not force:
            cached = await find_cached_narrative(
                db=self.db,
                report_id=report.id,
                product=report.product,
                prompt_version=prompt_version,
                input_hash=input_hash,
                model_name=model_name,
            )
            if cached is not None:
                logger.info(
                    "report_narrative_cache_hit",
                    report_id=str(report.id),
                    narrative_id=str(cached.id),
                    product=report.product,
                    prompt_version=prompt_version,
                    model_name=model_name,
                )
                report.status = "ready"
                report.error_message = None
                await self.db.flush()
                return cached

        narrative = await self._get_or_create_narrative_record(
            report=report,
            input_hash=input_hash,
            model_name=model_name,
            prompt_version=prompt_version,
            force_new=force,
        )
        return await self._generate_and_persist(
            report=report,
            narrative=narrative,
            narrative_input=narrative_input,
        )

    async def _generate_and_persist(
        self,
        *,
        report: Report,
        narrative: ReportNarrative,
        narrative_input: NarrativeInput,
    ) -> ReportNarrative:
        if self._should_use_staged_pipeline(report, narrative_input):
            return await self._generate_and_persist_staged(
                report=report,
                narrative=narrative,
                narrative_input=narrative_input,
            )
        prompt = build_self_story_prompt(narrative_input)
        now = datetime.now(UTC).replace(tzinfo=None)
        started_at = time.perf_counter()

        narrative.status = "generating"
        narrative.generation_attempts += 1
        narrative.generation_started_at = now
        narrative.generation_finished_at = None
        narrative.error_message = None
        report.status = "generating_narrative"
        report.error_message = None
        await self.db.flush()
        logger.info(
            "report_narrative_generation_started",
            report_id=str(report.id),
            narrative_id=str(narrative.id),
            product=report.product,
            prompt_version=narrative.prompt_version,
            model_provider=narrative.model_provider,
            model_name=narrative.model_name,
            attempt=narrative.generation_attempts,
        )

        try:
            candidate = await self.llm_provider.generate_structured(
                prompt=prompt,
                narrative_input=narrative_input,
                schema=SelfNarrative,
            )
        except LLMDisabledError as exc:
            logger.warning(
                "report_narrative_generation_degraded",
                report_id=str(report.id),
                narrative_id=str(narrative.id),
                product=report.product,
                failure_kind="provider_disabled",
                recovery_action="narrative_failed",
                duration_ms=_duration_ms(started_at),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return await self._save_failed_narrative(
                report=report,
                narrative=narrative,
                reason="Полный текстовый отчёт сейчас недоступен. Попробуйте позже.",
                duration_ms=_duration_ms(started_at),
                failure_kind="provider_disabled",
            )
        except LLMInvalidResponseError as exc:
            logger.warning(
                "report_narrative_generation_degraded",
                report_id=str(report.id),
                narrative_id=str(narrative.id),
                product=report.product,
                failure_kind="invalid_response",
                recovery_action="narrative_failed",
                duration_ms=_duration_ms(started_at),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return await self._save_failed_narrative(
                report=report,
                narrative=narrative,
                reason="Не удалось собрать полный текстовый отчёт. Попробуйте повторить генерацию.",
                duration_ms=_duration_ms(started_at),
                failure_kind="invalid_response",
            )
        except (LLMTimeoutError, LLMProviderUnavailableError) as exc:
            logger.warning(
                "report_narrative_generation_degraded",
                report_id=str(report.id),
                narrative_id=str(narrative.id),
                product=report.product,
                failure_kind="provider_timeout" if isinstance(exc, LLMTimeoutError) else "provider_unavailable",
                recovery_action="narrative_failed",
                duration_ms=_duration_ms(started_at),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return await self._save_failed_narrative(
                report=report,
                narrative=narrative,
                reason="Не удалось собрать полный текстовый отчёт. Попробуйте повторить генерацию.",
                duration_ms=_duration_ms(started_at),
                failure_kind=("provider_timeout" if isinstance(exc, LLMTimeoutError) else "provider_unavailable"),
            )

        errors = validate_self_narrative(candidate, narrative_input)
        repair_attempts_used = 0
        while errors:
            action = choose_narrative_recovery_action(
                errors=errors,
                repair_attempts_used=repair_attempts_used,
                llm_available=True,
            )
            logger.warning(
                "report_narrative_validation_failed",
                report_id=str(report.id),
                narrative_id=str(narrative.id),
                product=report.product,
                failure_kind="validation_failed",
                recovery_action=action,
                repair_attempts_used=repair_attempts_used,
                error_count=len(errors),
                duration_ms=_duration_ms(started_at),
            )
            if action == "repair":
                repair_attempts_used += 1
                candidate = await self.llm_provider.generate_structured(
                    prompt=_build_repair_prompt(prompt, errors),
                    narrative_input=narrative_input,
                    schema=SelfNarrative,
                )
                candidate = harden_self_narrative(candidate, narrative_input)
                errors = validate_self_narrative(candidate, narrative_input)
                continue
            if action == "fallback":
                hardened_candidate = harden_self_narrative(candidate, narrative_input)
                hardened_errors = validate_self_narrative(hardened_candidate, narrative_input)
                if not hardened_errors:
                    return await self._save_ready_narrative(
                        report=report,
                        narrative=narrative,
                        payload=hardened_candidate,
                        duration_ms=_duration_ms(started_at),
                        recovery_action="deterministic_hardening",
                    )
                return await self._save_failed_narrative(
                    report=report,
                    narrative=narrative,
                    reason="Не удалось собрать полный текстовый отчёт. Попробуйте повторить генерацию.",
                    duration_ms=_duration_ms(started_at),
                    failure_kind="validation_failed",
                )
            if action == "narrative_failed":
                return await self._save_failed_narrative(
                    report=report,
                    narrative=narrative,
                    reason=_format_validation_errors(errors),
                    duration_ms=_duration_ms(started_at),
                    failure_kind="validation_failed",
                )

        return await self._save_ready_narrative(
            report=report,
            narrative=narrative,
            payload=candidate,
            duration_ms=_duration_ms(started_at),
        )

    async def _generate_and_persist_staged(
        self,
        *,
        report: Report,
        narrative: ReportNarrative,
        narrative_input: NarrativeInput,
    ) -> ReportNarrative:
        synthesis = narrative_input.deep_natal_synthesis
        if synthesis is None:
            raise ValueError("staged self narrative requires deep_natal_synthesis")

        now = datetime.now(UTC).replace(tzinfo=None)
        started_at = time.perf_counter()
        narrative.status = "generating"
        narrative.generation_attempts += 1
        narrative.generation_started_at = now
        narrative.generation_finished_at = None
        narrative.error_message = None
        report.status = "generating_narrative"
        report.error_message = None
        logger.info(
            "report_narrative_generation_started",
            report_id=str(report.id),
            narrative_id=str(narrative.id),
            product=report.product,
            prompt_version=narrative.prompt_version,
            model_provider=narrative.model_provider,
            model_name=narrative.model_name,
            attempt=narrative.generation_attempts,
        )

        artifacts: dict[NarrativeStageId, NarrativeStageArtifact] = {
            "plan": NarrativeStageArtifact(
                stage_id="plan",
                status="running",
                prompt_version=_STAGE_PROMPT_VERSIONS["plan"],
                model_name=narrative.model_name,
                input_hash=_stable_hash({"DeepNatalSynthesis": synthesis.model_dump(mode="json")}),
                attempt_count=1,
                error_message=None,
                artifact=None,
            )
        }
        await self._persist_stage_runtime_snapshot(
            narrative=narrative,
            artifacts=artifacts,
            final_check=None,
        )
        try:
            plan = cast(
                NarrativePlan,
                await self._generate_staged_schema(
                    stage_id="plan",
                    prompt=build_stage_prompt("plan", synthesis=synthesis),
                    narrative_input=narrative_input,
                    schema=NarrativePlan,
                    narrative=narrative,
                    artifacts=artifacts,
                ),
            )
            artifacts["plan"] = NarrativeStageArtifact(
                stage_id="plan",
                status="ready",
                prompt_version=_STAGE_PROMPT_VERSIONS["plan"],
                model_name=narrative.model_name,
                input_hash=artifacts["plan"].input_hash,
                attempt_count=artifacts["plan"].attempt_count,
                error_message=None,
                artifact=plan.model_dump(mode="json"),
            )
            await self._persist_stage_runtime_snapshot(
                narrative=narrative,
                artifacts=artifacts,
                final_check=None,
            )

            stage_hashes = compute_stage_input_hashes(synthesis, plan)
            stage_outputs: dict[str, dict[str, Any]] = {}
            stage_schemas: list[
                tuple[
                    NarrativeStageId,
                    type[
                        IdentitySectionOutput
                        | EmotionalSectionOutput
                        | RelationshipSectionOutput
                        | DevelopmentSectionOutput
                        | HouseScenariosSectionOutput
                    ],
                ]
            ] = [
                ("identity", IdentitySectionOutput),
                ("emotional", EmotionalSectionOutput),
                ("relationships", RelationshipSectionOutput),
                ("development", DevelopmentSectionOutput),
                ("house_scenarios", HouseScenariosSectionOutput),
            ]
            for stage_id, schema in stage_schemas:
                artifacts[stage_id] = NarrativeStageArtifact(
                    stage_id=stage_id,
                    status="running",
                    prompt_version=_STAGE_PROMPT_VERSIONS[stage_id],
                    model_name=narrative.model_name,
                    input_hash=stage_hashes[stage_id],
                    attempt_count=1,
                    error_message=None,
                    artifact=None,
                )
                await self._persist_stage_runtime_snapshot(
                    narrative=narrative,
                    artifacts=artifacts,
                    final_check=None,
                )
                section_output = await self._generate_staged_schema(
                    stage_id=stage_id,
                    prompt=build_stage_prompt(stage_id, synthesis=synthesis),
                    narrative_input=narrative_input,
                    schema=schema,
                    narrative=narrative,
                    artifacts=artifacts,
                )
                payload = section_output.model_dump(mode="json")
                stage_outputs[stage_id] = payload
                artifacts[stage_id] = NarrativeStageArtifact(
                    stage_id=stage_id,
                    status="ready",
                    prompt_version=_STAGE_PROMPT_VERSIONS[stage_id],
                    model_name=narrative.model_name,
                    input_hash=stage_hashes[stage_id],
                    attempt_count=artifacts[stage_id].attempt_count,
                    error_message=None,
                    artifact=payload,
                )
                await self._persist_stage_runtime_snapshot(
                    narrative=narrative,
                    artifacts=artifacts,
                    final_check=None,
                )

            artifacts["assembly"] = NarrativeStageArtifact(
                stage_id="assembly",
                status="running",
                prompt_version=_STAGE_PROMPT_VERSIONS["assembly"],
                model_name=narrative.model_name,
                input_hash=stage_hashes["assembly"],
                attempt_count=1,
                error_message=None,
                artifact=None,
            )
            await self._persist_stage_runtime_snapshot(
                narrative=narrative,
                artifacts=artifacts,
                final_check=None,
            )
            final_check = cast(
                AssemblyCheck,
                await self._generate_staged_schema(
                    stage_id="assembly",
                    prompt=build_stage_prompt("assembly", synthesis=synthesis, stage_outputs=stage_outputs),
                    narrative_input=narrative_input,
                    schema=AssemblyCheck,
                    narrative=narrative,
                    artifacts=artifacts,
                ),
            )
            assembled = assemble_self_narrative(
                narrative_input=narrative_input,
                plan=plan,
                stage_outputs=cast(dict[str, object], stage_outputs),
                final_check=final_check,
            )
            errors = validate_assembled_self_narrative(assembled, narrative_input)
            if final_check.needs_retry or errors:
                artifacts["assembly"] = NarrativeStageArtifact(
                    stage_id="assembly",
                    status="failed",
                    prompt_version=_STAGE_PROMPT_VERSIONS["assembly"],
                    model_name=narrative.model_name,
                    input_hash=stage_hashes["assembly"],
                    attempt_count=1,
                    error_message=_format_validation_errors(errors) if errors else "assembly_requested_retry",
                    artifact=final_check.model_dump(mode="json"),
                )
                await self._persist_stage_runtime_snapshot(
                    narrative=narrative,
                    artifacts=artifacts,
                    final_check=final_check,
                )
                return await self._save_failed_narrative(
                    report=report,
                    narrative=narrative,
                    reason=(
                        _format_validation_errors(errors)
                        if errors
                        else "Не удалось собрать связный staged Self-отчёт. Попробуйте повторить генерацию."
                    ),
                    duration_ms=_duration_ms(started_at),
                    failure_kind="staged_validation_failed",
                    content=narrative.content,
                )

            artifacts["assembly"] = NarrativeStageArtifact(
                stage_id="assembly",
                status="ready",
                prompt_version=_STAGE_PROMPT_VERSIONS["assembly"],
                model_name=narrative.model_name,
                input_hash=stage_hashes["assembly"],
                attempt_count=artifacts["assembly"].attempt_count,
                error_message=None,
                artifact=final_check.model_dump(mode="json"),
            )
            progress = build_stage_progress_snapshot(artifacts, final_check=final_check)
            payload = assembled.model_dump(mode="json")
            payload["stage_progress"] = progress.model_dump(mode="json")
            payload["stage_artifacts"] = [artifact.model_dump(mode="json") for artifact in artifacts.values()]
            return await self._save_ready_narrative(
                report=report,
                narrative=narrative,
                payload=payload,
                duration_ms=_duration_ms(started_at),
            )
        except LLMDisabledError as exc:
            logger.warning(
                "report_narrative_generation_degraded",
                report_id=str(report.id),
                narrative_id=str(narrative.id),
                product=report.product,
                failure_kind="provider_disabled",
                recovery_action="narrative_failed",
                duration_ms=_duration_ms(started_at),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return await self._save_failed_narrative(
                report=report,
                narrative=narrative,
                reason="Полный текстовый отчёт сейчас недоступен. Попробуйте позже.",
                duration_ms=_duration_ms(started_at),
                failure_kind="provider_disabled",
                content=narrative.content,
            )
        except LLMInvalidResponseError as exc:
            logger.warning(
                "report_narrative_generation_degraded",
                report_id=str(report.id),
                narrative_id=str(narrative.id),
                product=report.product,
                failure_kind="invalid_response",
                recovery_action="narrative_failed",
                duration_ms=_duration_ms(started_at),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return await self._save_failed_narrative(
                report=report,
                narrative=narrative,
                reason="Не удалось собрать полный текстовый отчёт. Попробуйте повторить генерацию.",
                duration_ms=_duration_ms(started_at),
                failure_kind="invalid_response",
                content=narrative.content,
            )
        except (LLMTimeoutError, LLMProviderUnavailableError) as exc:
            logger.warning(
                "report_narrative_generation_degraded",
                report_id=str(report.id),
                narrative_id=str(narrative.id),
                product=report.product,
                failure_kind="provider_timeout" if isinstance(exc, LLMTimeoutError) else "provider_unavailable",
                recovery_action="narrative_failed",
                duration_ms=_duration_ms(started_at),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return await self._save_failed_narrative(
                report=report,
                narrative=narrative,
                reason="Не удалось собрать полный текстовый отчёт. Попробуйте повторить генерацию.",
                duration_ms=_duration_ms(started_at),
                failure_kind="provider_timeout" if isinstance(exc, LLMTimeoutError) else "provider_unavailable",
                content=narrative.content,
            )

    async def _persist_stage_runtime_snapshot(
        self,
        *,
        narrative: ReportNarrative,
        artifacts: dict[NarrativeStageId, NarrativeStageArtifact],
        final_check: AssemblyCheck | None,
    ) -> None:
        progress = build_stage_progress_snapshot(artifacts, final_check=final_check)
        base_content = narrative.content if isinstance(narrative.content, dict) else {}
        narrative.content = {
            **base_content,
            "stage_progress": progress.model_dump(mode="json"),
            "stage_artifacts": [artifact.model_dump(mode="json") for artifact in progress.stages],
        }
        await self.db.commit()

    async def _generate_staged_schema(
        self,
        *,
        stage_id: NarrativeStageId,
        prompt: str,
        narrative_input: NarrativeInput,
        schema: type[Any],
        narrative: ReportNarrative,
        artifacts: dict[NarrativeStageId, NarrativeStageArtifact],
    ) -> Any:
        artifact = artifacts[stage_id]
        max_attempts = max(1, _STAGED_INVALID_RESPONSE_MAX_ATTEMPTS)
        for attempt in range(artifact.attempt_count, max_attempts + 1):
            artifacts[stage_id] = NarrativeStageArtifact(
                stage_id=artifact.stage_id,
                status="running",
                prompt_version=artifact.prompt_version,
                model_name=artifact.model_name,
                input_hash=artifact.input_hash,
                attempt_count=attempt,
                error_message=None,
                artifact=None,
            )
            await self._persist_stage_runtime_snapshot(
                narrative=narrative,
                artifacts=artifacts,
                final_check=None,
            )
            attempt_prompt = (
                prompt
                if attempt == artifact.attempt_count
                else _build_staged_schema_retry_prompt(prompt, schema)
            )
            try:
                return await self.llm_provider.generate_structured(
                    prompt=attempt_prompt,
                    narrative_input=narrative_input,
                    schema=schema,
                )
            except LLMInvalidResponseError as exc:
                if attempt >= max_attempts:
                    artifacts[stage_id] = NarrativeStageArtifact(
                        stage_id=artifact.stage_id,
                        status="failed",
                        prompt_version=artifact.prompt_version,
                        model_name=artifact.model_name,
                        input_hash=artifact.input_hash,
                        attempt_count=attempt,
                        error_message=str(exc),
                        artifact=None,
                    )
                    await self._persist_stage_runtime_snapshot(
                        narrative=narrative,
                        artifacts=artifacts,
                        final_check=None,
                    )
                    raise
        raise AssertionError(f"unreachable staged generation path for stage {stage_id}")

    def _should_use_staged_pipeline(self, report: Report, narrative_input: NarrativeInput) -> bool:
        return (
            report.product == "self"
            and narrative_input.deep_natal_synthesis is not None
            and bool(getattr(self.llm_provider, "supports_staged_pipeline", False))
        )

    def _resolve_prompt_version(self, report: Report, narrative_input: NarrativeInput) -> str:
        if self._should_use_staged_pipeline(report, narrative_input):
            return _STAGED_SELF_PIPELINE_PROMPT_VERSION
        return SELF_STORY_PROMPT_VERSION

    async def _save_ready_narrative(
        self,
        *,
        report: Report,
        narrative: ReportNarrative,
        payload: SelfNarrative | dict[str, Any],
        reason: str | None = None,
        duration_ms: int | None = None,
        recovery_action: str | None = None,
    ) -> ReportNarrative:
        now = datetime.now(UTC).replace(tzinfo=None)
        narrative.status = "ready"
        narrative.content = payload.model_dump(mode="json") if isinstance(payload, SelfNarrative) else payload
        narrative.error_message = reason
        narrative.generation_finished_at = now
        report.status = "ready"
        report.error_message = None
        await self.db.flush()
        logger.info(
            "report_narrative_generation_succeeded",
            report_id=str(report.id),
            narrative_id=str(narrative.id),
            product=report.product,
            duration_ms=duration_ms,
            recovery_action=recovery_action,
            used_fallback=recovery_action is not None,
        )
        return narrative

    async def _save_failed_narrative(
        self,
        *,
        report: Report,
        narrative: ReportNarrative,
        reason: str,
        duration_ms: int | None = None,
        failure_kind: str = "generation_failed",
        content: dict[str, Any] | None = None,
    ) -> ReportNarrative:
        now = datetime.now(UTC).replace(tzinfo=None)
        narrative.status = "narrative_failed"
        narrative.content = content
        narrative.error_message = reason
        narrative.generation_finished_at = now
        report.status = "narrative_failed"
        report.error_message = reason
        await self.db.flush()
        logger.error(
            "report_narrative_generation_failed",
            report_id=str(report.id),
            narrative_id=str(narrative.id),
            product=report.product,
            duration_ms=duration_ms,
            failure_kind=failure_kind,
            error_message=reason,
        )
        return narrative

    async def _get_report(self, report_id: UUID) -> Report:
        result = await self.db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if report is None:
            raise NotFoundError("Report not found")
        return report

    async def _get_or_create_narrative_record(
        self,
        *,
        report: Report,
        input_hash: str,
        model_name: str,
        prompt_version: str,
        force_new: bool = False,
    ) -> ReportNarrative:
        existing = await _find_matching_narrative_record(
            db=self.db,
            report_id=report.id,
            product=report.product,
            prompt_versions=(prompt_version,),
            input_hash=input_hash,
            model_name=model_name,
        )
        if existing is not None:
            if force_new:
                existing.status = "pending"
                existing.content = None
                existing.error_message = None
                existing.generation_started_at = None
                existing.generation_finished_at = None
                await self.db.flush()
            return existing

        narrative = ReportNarrative(
            report_id=report.id,
            product=report.product,
            prompt_version=prompt_version,
            model_provider=self.app_settings.LLM_PROVIDER,
            model_name=model_name,
            status="pending",
            content=None,
            input_hash=input_hash,
        )
        self.db.add(narrative)
        try:
            await self.db.flush()
            return narrative
        except IntegrityError:
            await self.db.rollback()
            existing = await _find_matching_narrative_record(
                db=self.db,
                report_id=report.id,
                product=report.product,
                prompt_versions=(prompt_version,),
                input_hash=input_hash,
                model_name=model_name,
            )
            if existing is None:
                raise
            if force_new:
                existing.status = "pending"
                existing.content = None
                existing.error_message = None
                existing.generation_started_at = None
                existing.generation_finished_at = None
                await self.db.flush()
            logger.warning(
                "report_narrative_insert_race_reused_existing",
                report_id=str(report.id),
                narrative_id=str(existing.id),
                product=report.product,
                prompt_version=SELF_STORY_PROMPT_VERSION,
                model_name=model_name,
            )
            return existing


async def get_latest_narrative_for_report(
    *,
    db: AsyncSession,
    report_id: UUID,
    report: Report | None = None,
) -> ReportNarrative | None:
    """Return the latest persisted narrative row for a report.

    When the current report payload is available, ignore narrative rows whose input
    hash no longer matches the current deterministic report version.
    """
    if report is None:
        result = await db.execute(
            select(ReportNarrative)
            .where(ReportNarrative.report_id == report_id)
            .order_by(ReportNarrative.created_at.desc())
        )
        narrative = result.scalars().first()
        if narrative is not None and _is_legacy_fallback_narrative(narrative):
            return None
        return narrative

    if report.product != "self":
        result = await db.execute(
            select(ReportNarrative)
            .where(ReportNarrative.report_id == report_id)
            .order_by(ReportNarrative.created_at.desc())
        )
        return result.scalars().first()

    narrative_input = build_narrative_input(report)
    input_hash = compute_input_hash(narrative_input)
    narrative = await _find_matching_narrative_record(
        db=db,
        report_id=report_id,
        product=report.product,
        prompt_versions=(SELF_STORY_PROMPT_VERSION, _STAGED_SELF_PIPELINE_PROMPT_VERSION),
        input_hash=input_hash,
        model_name=None,
    )
    if narrative is not None and _is_legacy_fallback_narrative(narrative):
        return None
    return narrative


async def _find_matching_narrative_record(
    *,
    db: AsyncSession,
    report_id: UUID,
    product: str,
    prompt_versions: Sequence[str],
    input_hash: str,
    model_name: str | None,
) -> ReportNarrative | None:
    conditions: list[ColumnElement[bool]] = [
        ReportNarrative.report_id == report_id,
        ReportNarrative.product == product,
        ReportNarrative.prompt_version.in_(tuple(prompt_versions)),
        ReportNarrative.input_hash == input_hash,
    ]
    if model_name is not None:
        conditions.append(ReportNarrative.model_name == model_name)

    result = await db.execute(select(ReportNarrative).where(*conditions).order_by(ReportNarrative.created_at.desc()))
    return result.scalars().first()


def _is_legacy_fallback_narrative(narrative: ReportNarrative) -> bool:
    """Detect old fallback payloads that must not be shown as ready Self narratives."""
    if narrative.product != "self" or narrative.status != "ready":
        return False

    if narrative.error_message in {
        "provider_timeout_fallback",
        "provider_unavailable_fallback",
        "validation_fallback",
        "llm_disabled_fallback",
    }:
        return True

    content = narrative.content or {}
    if not isinstance(content, dict):
        return False

    hero = content.get("hero")
    hero_body = hero.get("body") if isinstance(hero, dict) else None
    final_summary = content.get("final_summary")

    if isinstance(hero_body, str) and (
        "безопасное резервное резюме" in hero_body or "детерминированное резюме" in hero_body
    ):
        return True

    return isinstance(final_summary, str) and "резервная детерминированная версия" in final_summary


async def find_cached_narrative(
    *,
    db: AsyncSession,
    report_id: UUID,
    product: str,
    prompt_version: str,
    input_hash: str,
    model_name: str,
) -> ReportNarrative | None:
    """Find an already generated narrative for the same cache key."""
    result = await db.execute(
        select(ReportNarrative).where(
            ReportNarrative.report_id == report_id,
            ReportNarrative.product == product,
            ReportNarrative.prompt_version == prompt_version,
            ReportNarrative.input_hash == input_hash,
            ReportNarrative.model_name == model_name,
            ReportNarrative.status == "ready",
        )
    )
    return result.scalar_one_or_none()


_STAGE_PROMPT_VERSIONS: dict[NarrativeStageId, str] = {
    "plan": "self_plan_v1",
    "identity": "self_section_identity_v1",
    "emotional": "self_section_emotional_v1",
    "relationships": "self_section_relationships_v1",
    "development": "self_section_development_v1",
    "house_scenarios": "self_section_house_scenarios_v1",
    "assembly": "self_assemble_v1",
}


def _stable_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_stage_input_hashes(
    synthesis: DeepNatalSynthesis,
    plan: NarrativePlan,
) -> dict[NarrativeStageId, str]:
    synthesis_payload = synthesis.model_dump(mode="json")
    hashes: dict[NarrativeStageId, str] = {
        "plan": _stable_hash({"DeepNatalSynthesis": synthesis_payload}),
    }
    section_map = {section.section_id: section for section in plan.sections}
    if "identity" in section_map:
        hashes["identity"] = _stable_hash(
            {
                "planet_roles": synthesis_payload["planet_roles"],
                "house_axis_patterns": synthesis_payload["house_axis_patterns"],
                "chart_dynamics": synthesis_payload["chart_dynamics"],
                "plan_section": section_map["identity"].model_dump(mode="json"),
            }
        )
    if "emotional" in section_map:
        hashes["emotional"] = _stable_hash(
            {
                "chart_dynamics": synthesis_payload["chart_dynamics"],
                "contradictions": synthesis_payload["contradictions"],
                "maturity_levels": synthesis_payload["maturity_levels"],
                "calibration_hypotheses": synthesis_payload["calibration_hypotheses"],
                "plan_section": section_map["emotional"].model_dump(mode="json"),
            }
        )
    if "relationships" in section_map:
        hashes["relationships"] = _stable_hash(
            {
                "aspect_patterns": synthesis_payload["aspect_patterns"],
                "chart_dynamics": synthesis_payload["chart_dynamics"],
                "contradictions": synthesis_payload["contradictions"],
                "plan_section": section_map["relationships"].model_dump(mode="json"),
            }
        )
    if "development" in section_map:
        hashes["development"] = _stable_hash(
            {
                "chart_dynamics": synthesis_payload["chart_dynamics"],
                "contradictions": synthesis_payload["contradictions"],
                "maturity_levels": synthesis_payload["maturity_levels"],
                "calibration_hypotheses": synthesis_payload["calibration_hypotheses"],
                "plan_section": section_map["development"].model_dump(mode="json"),
            }
        )
    if "house_scenarios" in section_map:
        hashes["house_scenarios"] = _stable_hash(
            {
                "house_axis_patterns": synthesis_payload["house_axis_patterns"],
                "planet_roles": synthesis_payload["planet_roles"],
                "plan_section": section_map["house_scenarios"].model_dump(mode="json"),
            }
        )
    hashes["assembly"] = _stable_hash(
        {
            "prompt_version": plan.prompt_version,
            "sections": [section.model_dump(mode="json") for section in plan.sections],
            "assembly_notes": plan.assembly_notes,
        }
    )
    return hashes


def reuse_cached_stage_artifacts(
    *,
    existing_artifacts: dict[str, dict[str, Any]] | dict[str, NarrativeStageArtifact],
    stage_input_hashes: dict[NarrativeStageId, str],
    model_name: str,
) -> dict[NarrativeStageId, NarrativeStageArtifact]:
    artifacts: dict[NarrativeStageId, NarrativeStageArtifact] = {}
    for stage_id, input_hash in stage_input_hashes.items():
        raw_existing = existing_artifacts.get(stage_id)
        existing = (
            raw_existing
            if isinstance(raw_existing, NarrativeStageArtifact)
            else NarrativeStageArtifact.model_validate(raw_existing)
            if raw_existing is not None
            else None
        )
        if (
            existing is not None
            and existing.model_name == model_name
            and existing.input_hash == input_hash
            and existing.status == "ready"
        ):
            artifacts[stage_id] = existing
            continue

        attempt_count = existing.attempt_count if existing is not None else 0
        artifacts[stage_id] = NarrativeStageArtifact(
            stage_id=stage_id,
            status="pending",
            prompt_version=_STAGE_PROMPT_VERSIONS[stage_id],
            model_name=model_name,
            input_hash=input_hash,
            attempt_count=attempt_count,
            error_message=None,
            artifact=existing.artifact if existing is not None and existing.status == "ready" else None,
        )
    return artifacts


def get_runnable_stages(artifacts: dict[NarrativeStageId, NarrativeStageArtifact]) -> list[NarrativeStageId]:
    plan_artifact = artifacts.get("plan")
    if plan_artifact is None or plan_artifact.status != "ready":
        return ["plan"] if plan_artifact is None or plan_artifact.status == "pending" else []

    section_stage_ids: list[NarrativeStageId] = [
        stage_id
        for stage_id in (
            "identity",
            "emotional",
            "relationships",
            "development",
            "house_scenarios",
        )
        if stage_id in artifacts
    ]
    runnable_sections = [stage_id for stage_id in section_stage_ids if artifacts[stage_id].status == "pending"]
    if runnable_sections:
        return runnable_sections

    if section_stage_ids and all(artifacts[stage_id].status == "ready" for stage_id in section_stage_ids):
        assembly_artifact = artifacts.get("assembly")
        if assembly_artifact is not None and assembly_artifact.status == "pending":
            return ["assembly"]
    return []


def build_stage_progress_snapshot(
    artifacts: dict[NarrativeStageId, NarrativeStageArtifact],
    *,
    final_check: AssemblyCheck | None,
) -> NarrativeStageProgress:
    ordered = [artifacts[key] for key in sorted(artifacts)]
    completed = sum(1 for artifact in ordered if artifact.status == "ready")
    current: NarrativeStageId | None = next(
        (artifact.stage_id for artifact in ordered if artifact.status == "running"), None
    )
    ready = (
        "assembly" in artifacts
        and artifacts["assembly"].status == "ready"
        and final_check is not None
        and not final_check.needs_retry
    )
    return NarrativeStageProgress(
        total_stages=len(ordered),
        completed_stages=completed,
        current_stage=current,
        ready=ready,
        stages=ordered,
    )


def _duration_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)


def _build_repair_prompt(prompt: str, errors: Sequence[object]) -> str:
    return f"{prompt}\n\nИсправь JSON строго по замечаниям валидатора:\n{_format_validation_errors(errors)}"


def _build_staged_schema_retry_prompt(prompt: str, schema: type[Any]) -> str:
    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
    top_level_keys = ", ".join(schema.model_fields.keys())
    return (
        f"{prompt}\n\n"
        "Предыдущий ответ не прошёл schema validation. "
        "Ответь СТРОГО валидным JSON-объектом без markdown и без пояснений. "
        f"Обязательные top-level keys: {top_level_keys}.\n"
        "Используй только строки/массивы/объекты, совместимые со схемой ниже.\n"
        f"JSON Schema:\n{schema_json}"
    )


def _format_validation_errors(errors: Sequence[object]) -> str:
    formatted: list[str] = []
    for error in errors:
        code = getattr(error, "code", "validation_error")
        location = getattr(error, "location", "unknown")
        message = getattr(error, "message", str(error))
        formatted.append(f"[{code}] {location}: {message}")
    return "; ".join(formatted)
