# ruff: noqa: RUF001
"""Narrative generation orchestration and storage helpers."""

from __future__ import annotations

import time
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, settings
from app.core.exceptions import NotFoundError
from app.modules.llm.exceptions import LLMDisabledError, LLMInvalidResponseError
from app.modules.llm.provider import LLMProvider, get_llm_provider
from app.modules.report_narratives.fallback import build_deterministic_self_fallback
from app.modules.report_narratives.hash import compute_input_hash
from app.modules.report_narratives.input_builder import build_narrative_input
from app.modules.report_narratives.models import ReportNarrative
from app.modules.report_narratives.prompts import SELF_STORY_PROMPT_VERSION, build_self_story_prompt
from app.modules.report_narratives.schemas import NarrativeInput, SelfNarrative
from app.modules.report_narratives.validators import (
    choose_narrative_recovery_action,
    validate_self_narrative,
)
from app.modules.reports.models import Report

logger = structlog.get_logger()


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

        if not force:
            cached = await find_cached_narrative(
                db=self.db,
                report_id=report.id,
                product=report.product,
                prompt_version=SELF_STORY_PROMPT_VERSION,
                input_hash=input_hash,
                model_name=model_name,
            )
            if cached is not None:
                logger.info(
                    "report_narrative_cache_hit",
                    report_id=str(report.id),
                    narrative_id=str(cached.id),
                    product=report.product,
                    prompt_version=SELF_STORY_PROMPT_VERSION,
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
                recovery_action="deterministic_fallback",
                duration_ms=_duration_ms(started_at),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return await self._save_ready_narrative(
                report=report,
                narrative=narrative,
                payload=build_deterministic_self_fallback(narrative_input, reason=str(exc)),
                reason=str(exc),
                duration_ms=_duration_ms(started_at),
                recovery_action="deterministic_fallback",
            )
        except LLMInvalidResponseError as exc:
            logger.error(
                "report_narrative_generation_failed",
                report_id=str(report.id),
                narrative_id=str(narrative.id),
                product=report.product,
                failure_kind="invalid_response",
                duration_ms=_duration_ms(started_at),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return await self._save_failed_narrative(
                report=report,
                narrative=narrative,
                reason=str(exc),
                duration_ms=_duration_ms(started_at),
                failure_kind="invalid_response",
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
                errors = validate_self_narrative(candidate, narrative_input)
                continue
            if action == "fallback":
                return await self._save_ready_narrative(
                    report=report,
                    narrative=narrative,
                    payload=build_deterministic_self_fallback(
                        narrative_input,
                        reason="Narrative generation failed validation and switched to deterministic fallback.",
                    ),
                    reason="validation_fallback",
                    duration_ms=_duration_ms(started_at),
                    recovery_action="validation_fallback",
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

    async def _save_ready_narrative(
        self,
        *,
        report: Report,
        narrative: ReportNarrative,
        payload: SelfNarrative,
        reason: str | None = None,
        duration_ms: int | None = None,
        recovery_action: str | None = None,
    ) -> ReportNarrative:
        now = datetime.now(UTC).replace(tzinfo=None)
        narrative.status = "ready"
        narrative.content = payload.model_dump(mode="json")
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
    ) -> ReportNarrative:
        now = datetime.now(UTC).replace(tzinfo=None)
        narrative.status = "narrative_failed"
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
        force_new: bool = False,
    ) -> ReportNarrative:
        result = await self.db.execute(
            select(ReportNarrative)
            .where(
                ReportNarrative.report_id == report.id,
                ReportNarrative.product == report.product,
                ReportNarrative.prompt_version == SELF_STORY_PROMPT_VERSION,
                ReportNarrative.input_hash == input_hash,
                ReportNarrative.model_name == model_name,
            )
            .order_by(ReportNarrative.created_at.desc())
        )
        existing = result.scalars().first()
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
            prompt_version=SELF_STORY_PROMPT_VERSION,
            model_provider=self.app_settings.LLM_PROVIDER,
            model_name=model_name,
            status="pending",
            content=None,
            input_hash=input_hash,
        )
        self.db.add(narrative)
        await self.db.flush()
        return narrative


async def get_latest_narrative_for_report(*, db: AsyncSession, report_id: UUID) -> ReportNarrative | None:
    """Return the latest persisted narrative row for a report."""
    result = await db.execute(
        select(ReportNarrative)
        .where(ReportNarrative.report_id == report_id)
        .order_by(ReportNarrative.created_at.desc())
    )
    return result.scalars().first()


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


def _duration_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)


def _build_repair_prompt(prompt: str, errors: Sequence[object]) -> str:
    return f"{prompt}\n\nИсправь JSON строго по замечаниям валидатора:\n{_format_validation_errors(errors)}"


def _format_validation_errors(errors: Sequence[object]) -> str:
    formatted: list[str] = []
    for error in errors:
        code = getattr(error, "code", "validation_error")
        location = getattr(error, "location", "unknown")
        message = getattr(error, "message", str(error))
        formatted.append(f"[{code}] {location}: {message}")
    return "; ".join(formatted)
