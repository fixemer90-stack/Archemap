# ruff: noqa: RUF001
"""Bounded Career LLM sections, validators, and deterministic-first assembly."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Protocol
from uuid import UUID

from app.modules.career.interpretation_facts import CareerInterpretationFacts, validate_interpretation_facts
from app.modules.career.models import CareerReport, CareerSegmentGeneration
from app.modules.career.narrative_schemas import CareerSectionRenderInput, CareerSegmentOutput

CAREER_PROMPT_VERSION = "career-segment-prompt-1"

_SECTION_METADATA: dict[str, tuple[str, str]] = {
    "professional_summary": ("Ваш профессиональный профиль", "Собрать главную профессиональную механику."),
    "work_style": ("Как вы работаете", "Объяснить рабочий ритм и способ организации задач."),
    "strengths": ("Сильные стороны", "Раскрыть практические сильные стороны без рейтинга личности."),
    "decision_making": ("Стиль принятия решений", "Показать механизм выбора и проверки решений."),
    "leadership_and_influence": ("Лидерство и влияние", "Разделить способность влиять и желание управлять."),
    "optimal_environment": ("Оптимальная рабочая среда", "Описать поддерживающие условия работы."),
    "risk_environment": ("Что может снижать эффективность", "Описать условные риски без запретов."),
    "career_archetypes": ("Профессиональные архетипы", "Объяснить несколько моделей, не назначая один тип."),
    "role_families": ("Подходящие типы ролей", "Объяснить классы ролей до примеров профессий."),
    "career_paths": ("Возможные карьерные траектории", "Показать переходы и prerequisites без гарантий."),
}


class CareerNarrativeValidationError(ValueError):
    """Raised when a Career section violates its curated input contract."""


class CareerSegmentProvider(Protocol):
    provider_name: str
    model_name: str

    async def generate_segment(
        self, *, prompt: str, section_input: CareerSectionRenderInput
    ) -> dict[str, Any]: ...


class StructuredCareerProvider(Protocol):
    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: Any,
        schema: type[CareerSegmentOutput],
    ) -> CareerSegmentOutput: ...


class StructuredCareerSegmentProviderAdapter:
    """Adapt the shared structured provider boundary to Career sections."""

    def __init__(
        self,
        *,
        provider: StructuredCareerProvider,
        provider_name: str,
        model_name: str,
    ) -> None:
        self._provider = provider
        self.provider_name = provider_name
        self.model_name = model_name

    async def generate_segment(
        self, *, prompt: str, section_input: CareerSectionRenderInput
    ) -> dict[str, Any]:
        response = await self._provider.generate_structured(
            prompt=prompt,
            narrative_input=section_input,
            schema=CareerSegmentOutput,
        )
        return response.model_dump(mode="json")


class MockCareerSegmentProvider:
    provider_name = "mock"
    model_name = "career-contract-mock-1"

    async def generate_segment(
        self, *, prompt: str, section_input: CareerSectionRenderInput
    ) -> dict[str, Any]:
        del prompt
        return CareerSegmentOutput(
            section_key=section_input.section_key,
            title=section_input.section_title,
            body=(
                "Этот раздел опирается на рассчитанные факты и показывает, как рабочая механика может "
                "проявляться в задачах. Вывод стоит проверять на реальном контексте роли: он описывает "
                "вероятный способ действия, а не обязательный сценарий или обещание результата."
            ),
            cited_fact_keys=list(section_input.owned_fact_keys),
        ).model_dump(mode="json")


def build_career_section_inputs(facts: CareerInterpretationFacts) -> list[CareerSectionRenderInput]:
    validate_interpretation_facts(facts)
    fact_index = _fact_index(facts)
    inputs: list[CareerSectionRenderInput] = []
    for section_key in _SECTION_METADATA:
        contract = facts.section_contracts[section_key]
        title, purpose = _SECTION_METADATA[section_key]
        inputs.append(
            CareerSectionRenderInput(
                profile_id=facts.profile_id,
                chart_id=facts.chart_id,
                section_key=section_key,
                section_title=title,
                section_purpose=purpose,
                owned_fact_keys=list(contract.owned_fact_keys),
                owned_facts=[fact_index[key] for key in contract.owned_fact_keys],
                reference_facts=[fact_index[key] for key in contract.reference_fact_keys],
                forbidden_fact_keys=list(contract.forbidden_fact_keys),
                style_contract={
                    "language": "ru",
                    "tone": "specific_soft_non_diagnostic",
                    "profession_examples": "conditional_only",
                    "low_confidence": "explicitly_conditional",
                },
                continuation_policy={"scope": "same_section_only", "allow_continuation": True},
            )
        )
    return inputs


def _fact_index(facts: CareerInterpretationFacts) -> dict[str, dict[str, Any]]:
    collections = (
        facts.top_dimensions,
        facts.low_dimensions,
        facts.career_archetypes,
        facts.preferred_environment,
        facts.risk_environment,
        facts.contradictions,
        facts.role_matches,
        facts.career_paths,
    )
    return {
        item.fact_key: item.model_dump(mode="json")
        for collection in collections
        for item in collection
    }


def build_segment_prompt(section_input: CareerSectionRenderInput) -> str:
    payload = json.dumps(section_input.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
    return f"""Write one section of a Russian Career report.
Use only owned_facts and bounded reference_facts from the provided JSON.
Cite every owned_fact_key. Do not expand forbidden_fact_keys.
Return JSON matching career_segment_output_v1; no markdown or text outside JSON.
Do not calculate scores, invent roles, paths, professions, chart facts, or user answers.
Profession examples must remain conditional illustrations, never prescriptions.
Do not promise income, hiring, success, diagnosis, or certainty.
Retain contradictions. Mark low-confidence conclusions as conditional.
If output is cut, request continuation for this same section only.
Section input:
{payload}"""


def validate_segment_output(
    *, output: CareerSegmentOutput, section_input: CareerSectionRenderInput
) -> CareerSegmentOutput:
    if output.section_key != section_input.section_key:
        raise CareerNarrativeValidationError("section mismatch")
    cited = set(output.cited_fact_keys)
    allowed = set(section_input.owned_fact_keys) | {
        str(item["fact_key"]) for item in section_input.reference_facts
    }
    unknown = cited - allowed
    if unknown:
        raise CareerNarrativeValidationError(f"unsupported facts: {sorted(unknown)}")
    missing = set(section_input.owned_fact_keys) - cited
    if missing:
        raise CareerNarrativeValidationError(f"missing owned facts: {sorted(missing)}")
    if cited & set(section_input.forbidden_fact_keys):
        raise CareerNarrativeValidationError("forbidden fact expansion")
    body = output.body.lower()
    if re.search(r"(^|\n)\s{0,3}#{1,6}\s|```", output.body):
        raise CareerNarrativeValidationError("markdown is forbidden")
    generic = ("вы уникальны", "раскройте свой потенциал", "найдите баланс", "следуйте своему сердцу")
    if sum(fragment in body for fragment in generic) >= 2:
        raise CareerNarrativeValidationError("generic narrative")
    if any(fragment in body for fragment in ("гарантирует", "гарантированный доход", "успешное трудоустройство")):
        raise CareerNarrativeValidationError("career overclaim")
    if re.search(r"\b(вам нужно|вы должны|вам следует)\s+(стать|работать)\b", body):
        raise CareerNarrativeValidationError("profession prescription")
    if not output.continuation_complete and not output.continuation_cursor:
        raise CareerNarrativeValidationError("continuation cursor required")
    return output


async def run_career_segment_generation(
    *,
    provider: CareerSegmentProvider,
    section_input: CareerSectionRenderInput,
    career_profile_id: UUID,
    chart_id: UUID,
    generation_id: UUID,
    prompt_version: str = CAREER_PROMPT_VERSION,
) -> CareerSegmentGeneration:
    prompt = build_segment_prompt(section_input)
    input_payload = section_input.model_dump(mode="json")
    try:
        raw = await provider.generate_segment(prompt=prompt, section_input=section_input)
        output = validate_segment_output(
            output=CareerSegmentOutput.model_validate(raw), section_input=section_input
        )
        status = "ready" if output.continuation_complete else "generating"
        return CareerSegmentGeneration(
            career_profile_id=career_profile_id,
            chart_id=chart_id,
            generation_id=generation_id,
            section_key=section_input.section_key,
            status=status,
            prompt_version=prompt_version,
            provider=provider.provider_name,
            model_version=provider.model_name,
            input_payload=input_payload | {"input_hash": _stable_hash(input_payload)},
            output_payload=output.model_dump(mode="json"),
            error=None,
        )
    except Exception:
        return CareerSegmentGeneration(
            career_profile_id=career_profile_id,
            chart_id=chart_id,
            generation_id=generation_id,
            section_key=section_input.section_key,
            status="failed",
            prompt_version=prompt_version,
            provider=provider.provider_name,
            model_version=provider.model_name,
            input_payload=input_payload | {"input_hash": _stable_hash(input_payload)},
            output_payload={},
            error="career_provider_failure",
        )


def build_deterministic_career_report_row(
    *,
    facts: CareerInterpretationFacts,
    generation_id: UUID,
    idempotency_key: str,
    version: int,
) -> CareerReport:
    validate_interpretation_facts(facts)
    return CareerReport(
        career_profile_id=facts.profile_id,
        chart_id=facts.chart_id,
        generation_id=generation_id,
        idempotency_key=idempotency_key,
        version=version,
        status="deterministic_ready",
        scoring_version=facts.scoring_version,
        reference_version=facts.curation_version,
        questionnaire_version="career-questionnaire-1",
        prompt_version=CAREER_PROMPT_VERSION,
        deterministic_payload=facts.model_dump(mode="json"),
        narrative_payload={"sections": [], "section_order": list(_SECTION_METADATA)},
        assembled_payload={
            "contract_version": "career_report_v1",
            "status": "deterministic_ready",
            "section_order": list(_SECTION_METADATA),
        },
    )


def assemble_career_report_row(
    *, report: CareerReport, segment_rows: list[CareerSegmentGeneration]
) -> CareerReport:
    ready_sections: list[dict[str, Any]] = []
    seen_bodies: set[str] = set()
    known_fact_keys = _deterministic_fact_keys(report.deterministic_payload)
    for section_key in _SECTION_METADATA:
        segment = next((item for item in segment_rows if item.section_key == section_key), None)
        if segment is None or segment.status != "ready":
            continue
        output = CareerSegmentOutput.model_validate(segment.output_payload)
        if not set(output.cited_fact_keys) <= known_fact_keys:
            raise CareerNarrativeValidationError("assembler cannot add new facts")
        canonical_body = " ".join(output.body.lower().split())
        if canonical_body in seen_bodies:
            raise CareerNarrativeValidationError("duplicate narrative section")
        seen_bodies.add(canonical_body)
        ready_sections.append(output.model_dump(mode="json"))

    failed = any(item.status == "failed" for item in segment_rows)
    if len(ready_sections) == len(_SECTION_METADATA):
        status = "ready"
    elif failed and not ready_sections:
        status = "narrative_failed"
    elif ready_sections:
        status = "generating_sections"
    else:
        status = report.status
    return CareerReport(
        career_profile_id=report.career_profile_id,
        chart_id=report.chart_id,
        generation_id=report.generation_id,
        idempotency_key=report.idempotency_key,
        version=report.version,
        status=status,
        scoring_version=report.scoring_version,
        reference_version=report.reference_version,
        questionnaire_version=report.questionnaire_version,
        prompt_version=report.prompt_version,
        deterministic_payload=dict(report.deterministic_payload),
        narrative_payload={"sections": ready_sections, "section_order": list(_SECTION_METADATA)},
        assembled_payload={
            **report.assembled_payload,
            "status": status,
            "segment_diagnostics": [
                {"section_key": item.section_key, "status": item.status, "error": item.error}
                for item in segment_rows
                if item.status != "ready"
            ],
        },
    )


def _deterministic_fact_keys(payload: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for name in (
        "top_dimensions", "low_dimensions", "career_archetypes", "preferred_environment",
        "risk_environment", "contradictions", "role_matches", "career_paths",
    ):
        keys.update(str(item["fact_key"]) for item in payload.get(name, []))
    return keys


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
