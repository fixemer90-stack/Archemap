# ruff: noqa: RUF001, E501
"""Unit tests for narrative generation service and task orchestration."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
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
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
    LLMTimeoutError,
)
from app.modules.report_narratives.assembler import assemble_self_narrative
from app.modules.report_narratives.fallback import build_deterministic_self_fallback
from app.modules.report_narratives.models import ReportNarrative
from app.modules.report_narratives.schemas import (
    AssemblyCheck,
    NarrativeInput,
    NarrativePlan,
)
from app.modules.report_narratives.service import ReportNarrativeService
from app.modules.report_narratives.tasks import (
    _generate_report_narrative_async,
    _run_async,
    finalize_narrative_task_failure,
    generate_report_narrative_task,
    should_retry_narrative_task_error,
)
from app.modules.report_narratives.validators import validate_assembled_self_narrative
from app.modules.reports.models import Report
from workers.tasks.reports import generate_report_narrative

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


class ReadyStagedProvider:
    model_name = "mock-self-v1"
    supports_staged_pipeline = True

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: NarrativeInput,
        schema: type[StructuredSchemaT],
    ) -> StructuredSchemaT:
        del prompt
        synthesis = narrative_input.deep_natal_synthesis
        assert synthesis is not None
        schema_name = schema.__name__
        self.calls.append(schema_name)

        if schema_name == "NarrativePlan":
            evidence_ids = list(synthesis.evidence_map.keys())[:3]
            return schema.model_validate(
                {
                    "prompt_version": "self_plan_v1",
                    "sections": [
                        {
                            "section_id": "identity",
                            "title": "Identity",
                            "required_evidence_ids": evidence_ids,
                            "focus": "Главная формула и сильные стороны.",
                        },
                        {
                            "section_id": "emotional",
                            "title": "Emotional",
                            "required_evidence_ids": evidence_ids,
                            "focus": "Эмоции, речь и уязвимости.",
                        },
                        {
                            "section_id": "relationships",
                            "title": "Relationships",
                            "required_evidence_ids": evidence_ids,
                            "focus": "Отношения и близость.",
                        },
                        {
                            "section_id": "development",
                            "title": "Development",
                            "required_evidence_ids": evidence_ids,
                            "focus": "Вектор развития.",
                        },
                        {
                            "section_id": "house_scenarios",
                            "title": "House scenarios",
                            "required_evidence_ids": evidence_ids,
                            "focus": "Жизненные сценарии и восприятие мира.",
                        },
                    ],
                    "global_guardrails": ["Только evidence-backed claims"],
                    "assembly_notes": "Собери единый narrative-first Self report.",
                }
            )
        if schema_name == "IdentitySectionOutput":
            return schema.model_validate(
                {
                    "section_id": "identity",
                    "title": "Identity",
                    "paragraphs": [
                        "Вы строите идентичность через смысл, точность и внутреннюю собранность.",
                        "В сильной форме это даёт ясность, дисциплину и способность держать свою линию.",
                    ],
                    "evidence_ids": ["sun_virgo_house_9", "moon_trine_mercury"],
                    "covered_pattern_ids": ["identity_pattern"],
                }
            )
        if schema_name == "EmotionalSectionOutput":
            return schema.model_validate(
                {
                    "section_id": "emotional",
                    "title": "Emotional",
                    "paragraphs": [
                        "Эмоции быстро связываются с мыслью, поэтому вы не просто чувствуете, а сразу пытаетесь это осмыслить.",
                        "Уязвимость появляется там, где внутреннее напряжение требует немедленного словесного контроля.",
                    ],
                    "evidence_ids": ["moon_trine_mercury", "moon_leo_house_8"],
                    "covered_pattern_ids": ["emotional_pattern"],
                }
            )
        if schema_name == "RelationshipSectionOutput":
            return schema.model_validate(
                {
                    "section_id": "relationships",
                    "title": "Relationships",
                    "paragraphs": [
                        "В отношениях вы ищете не формальную близость, а эмоциональную глубину и взаимную вовлечённость.",
                        "Сексуальность раскрывается там, где есть доверие, интенсивность и ощущение живого контакта.",
                    ],
                    "evidence_ids": ["moon_leo_house_8", "moon_trine_mercury"],
                    "covered_pattern_ids": ["relationship_pattern"],
                }
            )
        if schema_name == "DevelopmentSectionOutput":
            return schema.model_validate(
                {
                    "section_id": "development",
                    "title": "Development",
                    "paragraphs": [
                        "Ваш рост начинается там, где вы перестаёте чинить напряжение мгновенной реакцией и выдерживаете паузу.",
                        "Зрелость приходит, когда чувствительность превращается в наблюдение, а не в перегрузку.",
                    ],
                    "evidence_ids": ["moon_trine_mercury", "sun_virgo_house_9"],
                    "covered_pattern_ids": ["development_pattern"],
                }
            )
        if schema_name == "HouseScenariosSectionOutput":
            return schema.model_validate(
                {
                    "section_id": "house_scenarios",
                    "title": "House scenarios",
                    "paragraphs": [
                        "Вы воспринимаете мир через поиск смысла, глубины и скрытых взаимосвязей.",
                        "Жизненные сюжеты становятся наиболее плодотворными там, где есть исследование и внутренняя честность.",
                    ],
                    "evidence_ids": ["sun_virgo_house_9", "moon_leo_house_8"],
                    "covered_pattern_ids": ["house_pattern"],
                }
            )
        if schema_name == "AssemblyCheck":
            return schema.model_validate(
                {
                    "duplicate_claim_ids": [],
                    "missing_required_evidence_ids": [],
                    "tone_notes": ["Собранный текст держит плотный Self-first тон."],
                    "needs_retry": False,
                }
            )
        raise AssertionError(f"Unexpected schema for staged provider: {schema_name}")


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
        narrative.sections[0].body = "Этот текст звучит как диагноз и потому должен быть отклонён."
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


class SchemaInvalidProvider:
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
        raise LLMInvalidResponseError(
            "LLM provider returned JSON that does not match schema",
            code="llm_invalid_response",
        )


class FailingStagedProvider(ReadyStagedProvider):
    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: NarrativeInput,
        schema: type[StructuredSchemaT],
    ) -> StructuredSchemaT:
        if schema.__name__ == "EmotionalSectionOutput":
            raise LLMInvalidResponseError(
                "LLM provider returned JSON that does not match schema",
                code="llm_invalid_response",
            )
        return await super().generate_structured(
            prompt=prompt,
            narrative_input=narrative_input,
            schema=schema,
        )


class FlakyStagedProvider(ReadyStagedProvider):
    def __init__(self) -> None:
        super().__init__()
        self.identity_calls = 0

    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: NarrativeInput,
        schema: type[StructuredSchemaT],
    ) -> StructuredSchemaT:
        if schema.__name__ == "IdentitySectionOutput":
            self.identity_calls += 1
            if self.identity_calls == 1:
                raise LLMInvalidResponseError(
                    "LLM provider returned JSON that does not match schema",
                    code="llm_invalid_response",
                )
        return await super().generate_structured(
            prompt=prompt,
            narrative_input=narrative_input,
            schema=schema,
        )


class ParallelTrackingProvider(ReadyStagedProvider):
    def __init__(self) -> None:
        super().__init__()
        self.in_flight = 0
        self.max_in_flight = 0

    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: NarrativeInput,
        schema: type[StructuredSchemaT],
    ) -> StructuredSchemaT:
        is_section_schema = schema.__name__ in {
            "IdentitySectionOutput",
            "EmotionalSectionOutput",
            "RelationshipSectionOutput",
            "DevelopmentSectionOutput",
            "HouseScenariosSectionOutput",
        }
        if is_section_schema:
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
            await asyncio.sleep(0.02)
            try:
                return await super().generate_structured(
                    prompt=prompt,
                    narrative_input=narrative_input,
                    schema=schema,
                )
            finally:
                self.in_flight -= 1
        return await super().generate_structured(
            prompt=prompt,
            narrative_input=narrative_input,
            schema=schema,
        )


class TimeoutProvider:
    model_name = "deepseek-v4-pro"

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
        raise LLMTimeoutError("LLM provider request timed out", code="llm_timeout")


def test_report_tasks_import_registers_profile_table_in_metadata() -> None:
    output = subprocess.check_output(
        [
            sys.executable,
            "-c",
            (
                "from app.infrastructure.database import Base;"
                "import app.modules.report_narratives.tasks;"
                "print(sorted(Base.metadata.tables.keys()))"
            ),
        ],
        text=True,
    )
    assert "person_profiles" in output


def test_report_narrative_task_runner_reuses_process_event_loop() -> None:
    async def get_loop_id() -> int:
        import asyncio

        return id(asyncio.get_running_loop())

    first = _run_async(get_loop_id())
    second = _run_async(get_loop_id())

    assert first == second


def test_generate_report_narrative_task_has_extended_time_limits_for_staged_runtime() -> None:
    task_obj: Any = generate_report_narrative
    assert cast(int, task_obj.soft_time_limit) >= 600
    assert cast(int, task_obj.time_limit) >= 720


def test_assemble_self_narrative_avoids_duplicate_sexuality_when_relationships_has_one_paragraph() -> None:
    narrative_input = NarrativeInput.model_validate(make_narrative_input_payload())
    plan = NarrativePlan.model_validate(
        {
            "prompt_version": "self_plan_v1",
            "sections": [
                {
                    "section_id": section_id,
                    "title": section_id,
                    "required_evidence_ids": ["legacy_plan_fallback"],
                    "focus": section_id,
                }
                for section_id in ["identity", "emotional", "relationships", "development", "house_scenarios"]
            ],
            "global_guardrails": ["evidence-backed only"],
            "assembly_notes": "test",
        }
    )
    stage_outputs = {
        "identity": {
            "section_id": "identity",
            "title": "Identity",
            "paragraphs": ["Identity paragraph.", "Identity strength paragraph."],
            "evidence_ids": ["sun_virgo_house_9"],
            "covered_pattern_ids": ["identity_pattern"],
        },
        "emotional": {
            "section_id": "emotional",
            "title": "Emotional",
            "paragraphs": ["Emotional paragraph.", "Emotional vulnerability paragraph."],
            "evidence_ids": ["moon_trine_mercury"],
            "covered_pattern_ids": ["emotional_pattern"],
        },
        "relationships": {
            "section_id": "relationships",
            "title": "Relationships",
            "paragraphs": ["Single relationships paragraph."],
            "evidence_ids": ["moon_libra_house_8"],
            "covered_pattern_ids": ["relationship_pattern"],
        },
        "development": {
            "section_id": "development",
            "title": "Development",
            "paragraphs": ["Development paragraph.", "Development summary paragraph."],
            "evidence_ids": ["sun_virgo_house_9"],
            "covered_pattern_ids": ["development_pattern"],
        },
        "house_scenarios": {
            "section_id": "house_scenarios",
            "title": "House scenarios",
            "paragraphs": ["House paragraph.", "House summary paragraph."],
            "evidence_ids": ["sun_virgo_house_9"],
            "covered_pattern_ids": ["house_pattern"],
        },
    }
    final_check = AssemblyCheck.model_validate(
        {
            "duplicate_claim_ids": [],
            "missing_required_evidence_ids": [],
            "tone_notes": [],
            "needs_retry": False,
        }
    )

    narrative = assemble_self_narrative(
        narrative_input=narrative_input,
        plan=plan,
        stage_outputs=cast(dict[str, object], stage_outputs),
        final_check=final_check,
    )

    relationships_body = next(section.body for section in narrative.sections if section.id == "relationships")
    sexuality_body = next(section.body for section in narrative.sections if section.id == "sexuality")
    assert relationships_body != sexuality_body
    errors = validate_assembled_self_narrative(narrative, narrative_input)
    assert not any(error.code == "duplicate_paragraph" and error.location == "sections[sexuality]" for error in errors)


def test_assemble_self_narrative_sanitizes_invalid_identity_stage_output() -> None:
    narrative_input = NarrativeInput.model_validate(make_narrative_input_payload())
    plan = NarrativePlan.model_validate(
        {
            "prompt_version": "self_plan_v1",
            "sections": [
                {
                    "section_id": section_id,
                    "title": section_id,
                    "required_evidence_ids": ["legacy_plan_fallback"],
                    "focus": section_id,
                }
                for section_id in ["identity", "emotional", "relationships", "development", "house_scenarios"]
            ],
            "global_guardrails": ["evidence-backed only"],
            "assembly_notes": "test",
        }
    )
    stage_outputs = {
        "identity": {
            "section_id": "identity",
            "title": "Identity",
            "paragraphs": [
                "Identity is built from Sun in Capricorn and Moon in Libra with Mercury direction.",
            ],
            "evidence_ids": [
                "sun_virgo_house_9",
                "house_axis_house_scenario_sun_12",
                "chart_dynamic_identity_depth_axis",
            ],
            "covered_pattern_ids": ["identity_pattern"],
        },
        "emotional": {
            "section_id": "emotional",
            "title": "Emotional",
            "paragraphs": ["Эмоциональный абзац.", "Уязвимость собирается в ясный риск."],
            "evidence_ids": ["moon_trine_mercury"],
            "covered_pattern_ids": ["emotional_pattern"],
        },
        "relationships": {
            "section_id": "relationships",
            "title": "Relationships",
            "paragraphs": ["Абзац про отношения.", "Абзац про близость."],
            "evidence_ids": ["mercury_venus_jupiter_leo_8"],
            "covered_pattern_ids": ["relationship_pattern"],
        },
        "development": {
            "section_id": "development",
            "title": "Development",
            "paragraphs": ["Абзац развития.", "Итог развития."],
            "evidence_ids": ["sun_virgo_house_9"],
            "covered_pattern_ids": ["development_pattern"],
        },
        "house_scenarios": {
            "section_id": "house_scenarios",
            "title": "House scenarios",
            "paragraphs": ["Абзац про жизненные сценарии.", "Итог house scenarios."],
            "evidence_ids": ["sun_virgo_house_9"],
            "covered_pattern_ids": ["house_pattern"],
        },
    }
    final_check = AssemblyCheck.model_validate(
        {
            "duplicate_claim_ids": [],
            "missing_required_evidence_ids": [],
            "tone_notes": [],
            "needs_retry": False,
        }
    )

    narrative = assemble_self_narrative(
        narrative_input=narrative_input,
        plan=plan,
        stage_outputs=cast(dict[str, object], stage_outputs),
        final_check=final_check,
    )

    errors = validate_assembled_self_narrative(narrative, narrative_input)
    assert not any(error.code == "unsupported_domain_term" for error in errors)
    assert not any(error.code == "unknown_evidence_ref" for error in errors)
    assert not any(error.code == "duplicate_paragraph" and error.location == "sections[strengths]" for error in errors)


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


class FakeLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, object]]] = []

    def info(self, event: str, **kwargs: object) -> None:
        self.events.append(("info", event, kwargs))

    def warning(self, event: str, **kwargs: object) -> None:
        self.events.append(("warning", event, kwargs))

    def error(self, event: str, **kwargs: object) -> None:
        self.events.append(("error", event, kwargs))


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

        async def fake_get_or_create(
            *,
            report: Report,
            input_hash: str,
            model_name: str,
            prompt_version: str,
            force_new: bool = False,
        ) -> ReportNarrative:
            assert report is report_fixture
            assert input_hash
            assert model_name == "mock-self-v1"
            assert prompt_version in {"self_story_v5", "self_staged_v1"}
            assert force_new is False
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
    async def test_self_report_uses_staged_runtime_path_when_deep_synthesis_present(
        self,
        report_fixture: Report,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = AsyncMock()
        provider = ReadyStagedProvider()
        service = ReportNarrativeService(db=db, llm_provider=provider)
        record = make_narrative_record(report_fixture)

        monkeypatch.setattr(service, "_get_report", AsyncMock(return_value=report_fixture))
        monkeypatch.setattr(service, "_get_or_create_narrative_record", AsyncMock(return_value=record))
        monkeypatch.setattr("app.modules.report_narratives.service.find_cached_narrative", AsyncMock(return_value=None))

        result = await service.generate_for_report(report_fixture.id)

        assert provider.calls[0] == "NarrativePlan"
        assert provider.calls[-1] == "AssemblyCheck"
        assert set(provider.calls[1:-1]) == {
            "IdentitySectionOutput",
            "EmotionalSectionOutput",
            "RelationshipSectionOutput",
            "DevelopmentSectionOutput",
            "HouseScenariosSectionOutput",
        }
        assert result.status == "ready"
        assert result.content is not None
        assert result.content["title"] == f"Ваш внутренний портрет — {report_fixture.report_data['profile']['name']}"
        assert result.content["stage_progress"]["ready"] is True
        assert len(result.content["stage_artifacts"]) == 7
        assert {artifact["stage_id"] for artifact in result.content["stage_artifacts"]} == {
            "plan",
            "identity",
            "emotional",
            "relationships",
            "development",
            "house_scenarios",
            "assembly",
        }
        assert report_fixture.status == "ready"
        assert report_fixture.error_message is None

    @pytest.mark.asyncio
    async def test_staged_runtime_runs_section_generation_in_parallel_after_plan(
        self,
        report_fixture: Report,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = AsyncMock()
        provider = ParallelTrackingProvider()
        service = ReportNarrativeService(db=db, llm_provider=provider)
        record = make_narrative_record(report_fixture)

        monkeypatch.setattr(service, "_get_report", AsyncMock(return_value=report_fixture))
        monkeypatch.setattr(service, "_get_or_create_narrative_record", AsyncMock(return_value=record))
        monkeypatch.setattr("app.modules.report_narratives.service.find_cached_narrative", AsyncMock(return_value=None))

        result = await service.generate_for_report(report_fixture.id)

        assert result.status == "ready"
        assert provider.max_in_flight > 1

    @pytest.mark.asyncio
    async def test_staged_runtime_persists_progress_snapshots_before_final_ready(
        self,
        report_fixture: Report,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = AsyncMock()
        provider = ReadyStagedProvider()
        service = ReportNarrativeService(db=db, llm_provider=provider)
        record = make_narrative_record(report_fixture)
        snapshots: list[dict[str, Any] | None] = []

        async def capture_snapshot() -> None:
            if record.content is None:
                snapshots.append(None)
            else:
                snapshots.append(json.loads(json.dumps(record.content)))

        db.commit.side_effect = capture_snapshot
        monkeypatch.setattr(service, "_get_report", AsyncMock(return_value=report_fixture))
        monkeypatch.setattr(service, "_get_or_create_narrative_record", AsyncMock(return_value=record))
        monkeypatch.setattr("app.modules.report_narratives.service.find_cached_narrative", AsyncMock(return_value=None))

        result = await service.generate_for_report(report_fixture.id)

        assert result.status == "ready"
        persisted_progress = [snapshot for snapshot in snapshots if snapshot and snapshot.get("stage_progress")]
        assert persisted_progress
        assert db.commit.await_count >= 2
        assert persisted_progress[0]["stage_progress"]["current_stage"] == "plan"
        assert any(snapshot["stage_progress"]["current_stage"] is not None for snapshot in persisted_progress)

    @pytest.mark.asyncio
    async def test_staged_runtime_persists_progress_payload_on_failure(
        self,
        report_fixture: Report,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = AsyncMock()
        provider = FailingStagedProvider()
        service = ReportNarrativeService(db=db, llm_provider=provider)
        record = make_narrative_record(report_fixture)

        monkeypatch.setattr(service, "_get_report", AsyncMock(return_value=report_fixture))
        monkeypatch.setattr(service, "_get_or_create_narrative_record", AsyncMock(return_value=record))
        monkeypatch.setattr("app.modules.report_narratives.service.find_cached_narrative", AsyncMock(return_value=None))

        result = await service.generate_for_report(report_fixture.id)

        assert result.status == "narrative_failed"
        assert result.content is not None
        assert result.content["stage_progress"]["current_stage"] is None
        assert any(artifact["stage_id"] == "plan" for artifact in result.content["stage_artifacts"])
        assert any(
            artifact["stage_id"] == "emotional" and artifact["status"] == "failed"
            for artifact in result.content["stage_artifacts"]
        )

    @pytest.mark.asyncio
    async def test_staged_runtime_retries_invalid_response_once_and_recovers(
        self,
        report_fixture: Report,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = AsyncMock()
        provider = FlakyStagedProvider()
        service = ReportNarrativeService(db=db, llm_provider=provider)
        record = make_narrative_record(report_fixture)

        monkeypatch.setattr(service, "_get_report", AsyncMock(return_value=report_fixture))
        monkeypatch.setattr(service, "_get_or_create_narrative_record", AsyncMock(return_value=record))
        monkeypatch.setattr("app.modules.report_narratives.service.find_cached_narrative", AsyncMock(return_value=None))

        result = await service.generate_for_report(report_fixture.id)

        assert result.status == "ready"
        assert provider.identity_calls == 2
        assert result.content is not None
        identity_artifact = next(
            artifact for artifact in result.content["stage_artifacts"] if artifact["stage_id"] == "identity"
        )
        assert identity_artifact["status"] == "ready"
        assert identity_artifact["attempt_count"] == 2

    @pytest.mark.asyncio
    async def test_staged_runtime_logs_per_stage_metadata_and_retry_recovery(
        self,
        report_fixture: Report,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = AsyncMock()
        provider = FlakyStagedProvider()
        service = ReportNarrativeService(db=db, llm_provider=provider)
        record = make_narrative_record(report_fixture)
        fake_logger = FakeLogger()

        monkeypatch.setattr(service, "_get_report", AsyncMock(return_value=report_fixture))
        monkeypatch.setattr(service, "_get_or_create_narrative_record", AsyncMock(return_value=record))
        monkeypatch.setattr("app.modules.report_narratives.service.find_cached_narrative", AsyncMock(return_value=None))
        monkeypatch.setattr("app.modules.report_narratives.service.logger", fake_logger, raising=False)

        result = await service.generate_for_report(report_fixture.id)

        assert result.status == "ready"
        stage_started = [payload for _, event, payload in fake_logger.events if event == "report_narrative_stage_started"]
        stage_succeeded = [payload for _, event, payload in fake_logger.events if event == "report_narrative_stage_succeeded"]
        stage_failed = [payload for _, event, payload in fake_logger.events if event == "report_narrative_stage_failed"]

        assert any(payload.get("stage_id") == "plan" for payload in stage_started)
        assert any(payload.get("stage_id") == "assembly" for payload in stage_succeeded)
        assert any(
            payload.get("stage_id") == "identity"
            and payload.get("failure_kind") == "invalid_response"
            and payload.get("recovery_action") == "retry"
            for payload in stage_failed
        )
        assert any(
            payload.get("stage_id") == "identity"
            and payload.get("recovery_action") == "retry_recovered"
            and isinstance(payload.get("duration_ms"), int)
            and cast(int, payload.get("duration_ms")) >= 0
            for payload in stage_succeeded
        )
        assert all("model_name" in payload for payload in stage_started)
        assert all("prompt" not in payload for payload in stage_started + stage_succeeded + stage_failed)

    @pytest.mark.asyncio
    async def test_logs_generation_lifecycle_without_prompt_or_api_key(
        self,
        report_fixture: Report,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = AsyncMock()
        service = ReportNarrativeService(db=db, llm_provider=ReadyProvider())
        record = make_narrative_record(report_fixture)
        fake_logger = FakeLogger()

        monkeypatch.setattr(service, "_get_report", AsyncMock(return_value=report_fixture))
        monkeypatch.setattr(service, "_get_or_create_narrative_record", AsyncMock(return_value=record))
        monkeypatch.setattr("app.modules.report_narratives.service.find_cached_narrative", AsyncMock(return_value=None))
        monkeypatch.setattr("app.modules.report_narratives.service.logger", fake_logger, raising=False)

        await service.generate_for_report(report_fixture.id)

        event_names = [event for _, event, _ in fake_logger.events]
        assert "report_narrative_generation_started" in event_names
        assert "report_narrative_generation_succeeded" in event_names

        for _, _, payload in fake_logger.events:
            assert "prompt" not in payload
            assert "api_key" not in payload
            for value in payload.values():
                assert "super-secret-key" not in str(value)

    @pytest.mark.asyncio
    async def test_invalid_provider_response_marks_narrative_failed_without_fallback_summary(
        self,
        report_fixture: Report,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = AsyncMock()
        service = ReportNarrativeService(db=db, llm_provider=SchemaInvalidProvider())
        record = make_narrative_record(report_fixture)

        monkeypatch.setattr(service, "_get_report", AsyncMock(return_value=report_fixture))
        monkeypatch.setattr(service, "_get_or_create_narrative_record", AsyncMock(return_value=record))
        monkeypatch.setattr("app.modules.report_narratives.service.find_cached_narrative", AsyncMock(return_value=None))

        result = await service.generate_for_report(report_fixture.id)

        assert result.status == "narrative_failed"
        assert result.content is None
        assert result.error_message == "Не удалось собрать полный текстовый отчёт. Попробуйте повторить генерацию."
        assert report_fixture.status == "narrative_failed"
        assert report_fixture.error_message == result.error_message

    @pytest.mark.asyncio
    async def test_timeout_provider_response_marks_narrative_failed_without_fallback_summary(
        self,
        report_fixture: Report,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = AsyncMock()
        service = ReportNarrativeService(db=db, llm_provider=TimeoutProvider())
        record = make_narrative_record(report_fixture)

        monkeypatch.setattr(service, "_get_report", AsyncMock(return_value=report_fixture))
        monkeypatch.setattr(service, "_get_or_create_narrative_record", AsyncMock(return_value=record))
        monkeypatch.setattr("app.modules.report_narratives.service.find_cached_narrative", AsyncMock(return_value=None))

        result = await service.generate_for_report(report_fixture.id)

        assert result.status == "narrative_failed"
        assert result.content is None
        assert result.error_message == "Не удалось собрать полный текстовый отчёт. Попробуйте повторить генерацию."
        assert report_fixture.status == "narrative_failed"
        assert report_fixture.error_message == result.error_message

    @pytest.mark.asyncio
    async def test_logs_validation_failure_for_invalid_output(
        self,
        report_fixture: Report,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db = AsyncMock()
        service = ReportNarrativeService(db=db, llm_provider=NonRecoverableInvalidProvider())
        record = make_narrative_record(report_fixture)
        fake_logger = FakeLogger()

        monkeypatch.setattr(service, "_get_report", AsyncMock(return_value=report_fixture))
        monkeypatch.setattr(service, "_get_or_create_narrative_record", AsyncMock(return_value=record))
        monkeypatch.setattr("app.modules.report_narratives.service.find_cached_narrative", AsyncMock(return_value=None))
        monkeypatch.setattr("app.modules.report_narratives.service.logger", fake_logger, raising=False)

        result = await service.generate_for_report(report_fixture.id)

        validation_events = [
            payload for _, event, payload in fake_logger.events if event == "report_narrative_validation_failed"
        ]
        success_events = [
            payload for _, event, payload in fake_logger.events if event == "report_narrative_generation_succeeded"
        ]
        assert result.status == "ready"
        assert validation_events
        assert any(payload.get("failure_kind") == "validation_failed" for payload in validation_events)
        assert any(payload.get("recovery_action") == "repair" for payload in validation_events)
        assert success_events

    @pytest.mark.asyncio
    async def test_recoverable_validation_failure_recovers_after_single_repair_attempt(
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
        assert report_fixture.status == "ready"
        assert report_fixture.error_message is None

    @pytest.mark.asyncio
    async def test_validation_failure_can_be_sanitized_without_fallback_summary(
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

        assert result.status == "ready"
        assert result.content is not None
        assert report_fixture.status == "ready"
        assert report_fixture.error_message is None

    @pytest.mark.asyncio
    async def test_force_regenerate_reuses_existing_cache_key_record(
        self,
        report_fixture: Report,
    ) -> None:
        db = AsyncMock()
        service = ReportNarrativeService(db=db, llm_provider=ReadyProvider())
        existing = make_narrative_record(report_fixture)
        existing.status = "narrative_failed"
        existing.content = {"stale": True}
        existing.error_message = "previous failure"
        existing.generation_started_at = None
        existing.generation_finished_at = None

        query_result = SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: existing))
        db.execute = AsyncMock(return_value=query_result)

        result = await service._get_or_create_narrative_record(
            report=report_fixture,
            input_hash="hash123",
            model_name="mock-self-v1",
            prompt_version="self_story_v5",
            force_new=True,
        )

        assert result is existing
        assert existing.status == "pending"
        assert existing.content is None
        assert existing.error_message is None
        assert existing.generation_started_at is None
        assert existing.generation_finished_at is None
        db.add.assert_not_called()
        db.flush.assert_awaited_once()


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

        async def fake_async_task(input_report_id: object, *, force: bool = False) -> SimpleNamespace:
            assert input_report_id == report_id
            assert force is False
            return SimpleNamespace(id=narrative_id, status="ready")

        monkeypatch.setattr("app.modules.report_narratives.tasks._generate_report_narrative_async", fake_async_task)

        result = generate_report_narrative_task(str(report_id))

        assert result == {
            "report_id": str(report_id),
            "narrative_id": str(narrative_id),
            "status": "ready",
        }

    @pytest.mark.asyncio
    async def test_async_task_rolls_back_on_generation_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        report_id = uuid4()
        db = AsyncMock()

        monkeypatch.setattr(
            "app.modules.report_narratives.tasks.async_session_factory",
            lambda: _AsyncSessionContext(db),
        )
        monkeypatch.setattr(
            ReportNarrativeService,
            "generate_for_report",
            AsyncMock(side_effect=RuntimeError("boom")),
        )

        with pytest.raises(RuntimeError, match="boom"):
            await _generate_report_narrative_async(report_id)

        db.rollback.assert_awaited_once()
        db.commit.assert_not_awaited()

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
