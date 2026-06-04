# ruff: noqa: RUF001
"""Unit tests for narrative generation service and task orchestration."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, TypeVar, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import BaseModel
from tests.unit.test_report_narratives.test_schemas import make_narrative_input_payload

from app.core.exceptions import NotFoundError
from app.modules.llm.exceptions import (
    LLMDisabledError,
    LLMProviderUnavailableError,
    LLMTimeoutError,
)
from app.modules.report_narratives.fallback import build_deterministic_self_fallback
from app.modules.report_narratives.models import ReportNarrative
from app.modules.report_narratives.schemas import NarrativeInput
from app.modules.report_narratives.service import ReportNarrativeService
from app.modules.report_narratives.tasks import (
    finalize_narrative_task_failure,
    generate_report_narrative_task,
    should_retry_narrative_task_error,
)
from app.modules.reports.models import Report

StructuredSchemaT = TypeVar("StructuredSchemaT", bound=BaseModel)


class _AsyncSessionContext:
    def __init__(self, db: AsyncMock) -> None:
        self._db = db

    async def __aenter__(self) -> AsyncMock:
        return self._db

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


class ReadyProvider:
    model_name = "mock-self-v1"

    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: NarrativeInput,
        schema: type[StructuredSchemaT],
    ) -> StructuredSchemaT:
        del prompt
        return schema.model_validate(build_deterministic_self_fallback(narrative_input))


class RecoverableInvalidProvider:
    model_name = "mock-self-v1"

    def __init__(self) -> None:
        self.calls = 0

    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: NarrativeInput,
        schema: type[StructuredSchemaT],
    ) -> StructuredSchemaT:
        del prompt
        self.calls += 1
        narrative = build_deterministic_self_fallback(narrative_input)
        narrative.hero.evidence_notes[0].fact_ids = ["unknown_fact"]
        return schema.model_validate(narrative)


class NonRecoverableInvalidProvider:
    model_name = "mock-self-v1"

    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: NarrativeInput,
        schema: type[StructuredSchemaT],
    ) -> StructuredSchemaT:
        del prompt
        narrative = build_deterministic_self_fallback(narrative_input)
        narrative.sections[0].body = "Вам нужна денежная стратегия и список профессий."
        return schema.model_validate(narrative)


class NeverCalledProvider:
    model_name = "mock-self-v1"

    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: NarrativeInput,
        schema: type[StructuredSchemaT],
    ) -> StructuredSchemaT:
        del prompt
        del narrative_input
        del schema
        raise AssertionError("Provider must not be called when cache hit exists")


@pytest.fixture
def report_fixture() -> Report:
    payload = cast(dict[str, Any], make_narrative_input_payload())
    archetype = cast(dict[str, Any], payload["archetype"])
    return Report(
        id=uuid4(),
        user_id=uuid4(),
        profile_id=uuid4(),
        product="self",
        version=1,
        status="generating_narrative",
        mode="full",
        report_data={
            "profile": payload["profile"],
            "archetype": {
                "primary": archetype["primary"],
                "confidence": {"label": archetype["confidence_label"]},
                "explanation": archetype["explanation"],
            },
            "socionics": payload["socionics"],
            "chart": {
                "planets": [
                    {"name": "Sun", "sign": "Virgo", "house": 9},
                    {"name": "Moon", "sign": "Leo", "house": 8},
                ],
                "aspects": [
                    {
                        "planet_a": "Moon",
                        "planet_b": "Mercury",
                        "aspect_type": "trine",
                        "orb": 0.5,
                        "is_applying": True,
                    }
                ],
            },
            "claims": [
                {
                    "claim_id": "strength_expression",
                    "section": "strengths",
                    "message": "Вы умеете заражать идеей.",
                    "basis": [{"rule_id": "sun_virgo_house_9"}],
                },
                {
                    "claim_id": "risk_overload",
                    "section": "risks",
                    "message": "Иногда эмоции перегружают речь.",
                    "basis": [{"rule_id": "moon_trine_mercury"}],
                },
                {
                    "claim_id": "relationships_depth",
                    "section": "relationships",
                    "message": "Вам важна эмоциональная интенсивность и глубина доверия.",
                    "basis": [{"rule_id": "moon_leo_house_8"}],
                },
                {
                    "claim_id": "sexuality_intensity",
                    "section": "sexuality",
                    "message": "Близость раскрывается через доверие и внутреннюю вовлечённость.",
                    "basis": [{"rule_id": "moon_leo_house_8"}],
                },
                {
                    "claim_id": "development_grounding",
                    "section": "development",
                    "message": "Полезно давать себе паузу перед эмоционально важным разговором.",
                    "basis": [{"rule_id": "moon_trine_mercury"}],
                },
            ],
            "quality_warning": None,
        },
    )


def make_narrative_record(report: Report) -> ReportNarrative:
    return ReportNarrative(
        report_id=report.id,
        product="self",
        prompt_version="self_story_v1",
        model_provider="mock",
        model_name="mock-self-v1",
        status="pending",
        content=None,
        input_hash="hash123",
    )


class TestReportNarrativeService:
    @pytest.mark.asyncio
    async def test_reuses_cached_narrative_without_duplicate_generation(
        self,
        report_fixture: Report,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = AsyncMock()
        service = ReportNarrativeService(db=db, llm_provider=NeverCalledProvider())
        cached = make_narrative_record(report_fixture)
        cached.status = "ready"
        cached.content = {"title": "Кэш", "sections": []}

        async def fake_get_report(report_id: object) -> Report:
            assert report_id == report_fixture.id
            return report_fixture

        async def fake_find_cached(**kwargs: object) -> ReportNarrative:
            assert kwargs["report_id"] == report_fixture.id
            return cached

        monkeypatch.setattr(service, "_get_report", fake_get_report)
        monkeypatch.setattr("app.modules.report_narratives.service.find_cached_narrative", fake_find_cached)

        result = await service.generate_for_report(report_fixture.id)

        assert result is cached
        assert report_fixture.status == "ready"

    @pytest.mark.asyncio
    async def test_saves_ready_narrative_and_marks_report_ready(
        self,
        report_fixture: Report,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = AsyncMock()
        service = ReportNarrativeService(db=db, llm_provider=ReadyProvider())
        record = make_narrative_record(report_fixture)

        async def fake_get_report(report_id: object) -> Report:
            assert report_id == report_fixture.id
            return report_fixture

        async def fake_find_cached(**kwargs: object) -> None:
            return None

        async def fake_get_or_create(*, report: Report, input_hash: str, model_name: str) -> ReportNarrative:
            assert report is report_fixture
            assert input_hash
            assert model_name == "mock-self-v1"
            return record

        monkeypatch.setattr(service, "_get_report", fake_get_report)
        monkeypatch.setattr(service, "_get_or_create_narrative_record", fake_get_or_create)
        monkeypatch.setattr("app.modules.report_narratives.service.find_cached_narrative", fake_find_cached)

        result = await service.generate_for_report(report_fixture.id)

        assert result.status == "ready"
        assert result.generation_attempts == 1
        assert result.content is not None
        assert result.content["title"] == "Ваш внутренний портрет"
        assert report_fixture.status == "ready"
        assert report_fixture.error_message is None

    @pytest.mark.asyncio
    async def test_recoverable_validation_failure_falls_back_after_single_repair_attempt(
        self,
        report_fixture: Report,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = AsyncMock()
        provider = RecoverableInvalidProvider()
        service = ReportNarrativeService(db=db, llm_provider=provider)
        record = make_narrative_record(report_fixture)

        monkeypatch.setattr(service, "_get_report", AsyncMock(return_value=report_fixture))
        monkeypatch.setattr(service, "_get_or_create_narrative_record", AsyncMock(return_value=record))
        monkeypatch.setattr("app.modules.report_narratives.service.find_cached_narrative", AsyncMock(return_value=None))

        result = await service.generate_for_report(report_fixture.id)

        assert provider.calls == 2
        assert result.status == "ready"
        assert result.content is not None
        assert "текстовая версия" in result.content["hero"]["body"].lower()
        assert report_fixture.status == "ready"

    @pytest.mark.asyncio
    async def test_nonrecoverable_validation_failure_marks_report_and_narrative_failed(
        self,
        report_fixture: Report,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = AsyncMock()
        service = ReportNarrativeService(db=db, llm_provider=NonRecoverableInvalidProvider())
        record = make_narrative_record(report_fixture)

        monkeypatch.setattr(service, "_get_report", AsyncMock(return_value=report_fixture))
        monkeypatch.setattr(service, "_get_or_create_narrative_record", AsyncMock(return_value=record))
        monkeypatch.setattr("app.modules.report_narratives.service.find_cached_narrative", AsyncMock(return_value=None))

        result = await service.generate_for_report(report_fixture.id)

        assert result.status == "narrative_failed"
        assert result.error_message is not None
        assert report_fixture.status == "narrative_failed"
        assert report_fixture.error_message is not None


class TestNarrativeTasks:
    def test_classifies_retryable_task_errors(self) -> None:
        assert should_retry_narrative_task_error(LLMTimeoutError("timeout", code="llm_timeout")) is True
        assert (
            should_retry_narrative_task_error(
                LLMProviderUnavailableError("provider unavailable", code="llm_provider_unavailable")
            )
            is True
        )
        assert should_retry_narrative_task_error(LLMDisabledError("disabled", code="llm_disabled")) is False
        assert should_retry_narrative_task_error(NotFoundError("missing")) is False
        assert should_retry_narrative_task_error(RuntimeError("boom")) is False

    def test_sync_task_wraps_async_generation_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        report_id = uuid4()
        narrative_id = uuid4()

        async def fake_async_task(input_report_id: object) -> SimpleNamespace:
            assert input_report_id == report_id
            return SimpleNamespace(id=narrative_id, status="ready")

        monkeypatch.setattr("app.modules.report_narratives.tasks._generate_report_narrative_async", fake_async_task)

        result = generate_report_narrative_task(str(report_id))

        assert result == {
            "report_id": str(report_id),
            "narrative_id": str(narrative_id),
            "status": "ready",
        }

    def test_finalize_failure_marks_report_and_narrative_failed(
        self,
        report_fixture: Report,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = AsyncMock()
        narrative = make_narrative_record(report_fixture)
        report_result = SimpleNamespace(scalar_one_or_none=lambda: report_fixture)
        narrative_result = SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: narrative))
        db.execute = AsyncMock(side_effect=[report_result, narrative_result])

        monkeypatch.setattr(
            "app.modules.report_narratives.tasks.async_session_factory",
            lambda: _AsyncSessionContext(db),
        )

        finalize_narrative_task_failure(str(report_fixture.id), "provider timed out")

        assert report_fixture.status == "narrative_failed"
        assert report_fixture.error_message == "provider timed out"
        assert narrative.status == "narrative_failed"
        assert narrative.error_message == "provider timed out"
        db.commit.assert_awaited_once()
