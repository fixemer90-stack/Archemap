# ruff: noqa: RUF001
"""Bounded Career LLM sections, validators, and deterministic-first assembly."""

from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher
from typing import Any, Protocol
from uuid import UUID

from pydantic import ValidationError

from app.config import settings
from app.modules.career.interpretation_facts import CareerInterpretationFacts, validate_interpretation_facts
from app.modules.career.models import CareerReport, CareerSegmentGeneration
from app.modules.career.narrative_schemas import (
    CareerNarrativeClaim,
    CareerSectionRenderInput,
    CareerSegmentOutput,
)
from app.modules.career.observability import career_telemetry, estimate_provider_usage

CAREER_PROMPT_VERSION = "career-segment-prompt-5"

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
CAREER_SECTION_ORDER: tuple[str, ...] = tuple(_SECTION_METADATA)


class CareerNarrativeValidationError(ValueError):
    """Raised when a Career section violates its curated input contract."""


class CareerSegmentProvider(Protocol):
    provider_name: str
    model_name: str

    async def generate_segment(self, *, prompt: str, section_input: CareerSectionRenderInput) -> dict[str, Any]: ...


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

    async def generate_segment(self, *, prompt: str, section_input: CareerSectionRenderInput) -> dict[str, Any]:
        response = await self._provider.generate_structured(
            prompt=prompt,
            narrative_input=section_input,
            schema=CareerSegmentOutput,
        )
        return response.model_dump(mode="json")


class MockCareerSegmentProvider:
    provider_name = "mock"
    model_name = "career-contract-mock-1"

    async def generate_segment(self, *, prompt: str, section_input: CareerSectionRenderInput) -> dict[str, Any]:
        del prompt
        claims = [_mock_claim(fact, section_input.section_purpose) for fact in section_input.owned_facts]
        return CareerSegmentOutput(
            section_key=section_input.section_key,
            title=section_input.section_title,
            body=f"{section_input.section_title}. {' '.join(claim.text for claim in claims)}",
            cited_fact_keys=list(section_input.owned_fact_keys),
            claims=claims,
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
                    "profession_language": "ru",
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
    return {item.fact_key: item.model_dump(mode="json") for collection in collections for item in collection}


def build_segment_prompt(section_input: CareerSectionRenderInput) -> str:
    payload = json.dumps(section_input.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
    return f"""Write one section of a Russian Career report.
Use only owned_facts and bounded reference_facts from the provided JSON.
Cite every owned_fact_key. Do not expand forbidden_fact_keys.
Return structured claims with exact fact_keys. Every claim text must appear in body.
For low-confidence facts set conditional=true and use explicit conditional wording in the claim text.
Return JSON matching career_segment_output_v2 with exactly these fields and nothing else:
{{"section_key": "<copy section_key from the section input>",
 "title": "<copy section_title of this section>",
 "body": "<the whole section as Russian prose in one string>",
 "cited_fact_keys": ["<every owned_fact_key you cite>"],
 "claims": [{{"text": "<claim sentence copied verbatim from body>",
             "fact_keys": ["<the exact fact_key supporting this claim>"],
             "conditional": false}}],
 "continuation_complete": true,
 "continuation_cursor": null}}
Claim objects use "text" (never "claim" or "claim_text") and "fact_keys" as a list (never "fact_key").
No markdown and no text outside JSON.
Do not calculate scores, invent roles, paths, professions, chart facts, or user answers.
Profession examples must remain conditional illustrations, never prescriptions.
Write every profession name in Russian. Do not leave profession names in English.
Do not promise income, hiring, success, diagnosis, or certainty.
Never write the phrases «гарантирует», «гарантированный доход», «успешное трудоустройство», «вы уникальны»,
«раскройте свой потенциал», «найдите баланс», «следуйте своему сердцу».
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
    allowed = set(section_input.owned_fact_keys) | {str(item["fact_key"]) for item in section_input.reference_facts}
    unknown = cited - allowed
    if unknown:
        raise CareerNarrativeValidationError(f"unsupported facts: {sorted(unknown)}")
    missing = set(section_input.owned_fact_keys) - cited
    if missing:
        raise CareerNarrativeValidationError(f"missing owned facts: {sorted(missing)}")
    if cited & set(section_input.forbidden_fact_keys):
        raise CareerNarrativeValidationError("forbidden fact expansion")
    _validate_claims(output=output, section_input=section_input, allowed=allowed)
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
    if re.search(r"\b(диагностирован|диагностировано|расстройство|патология|психическое заболевание)\b", body):
        raise CareerNarrativeValidationError("diagnostic language")
    if not output.continuation_complete and not output.continuation_cursor:
        raise CareerNarrativeValidationError("continuation cursor required")
    return output


def _mock_claim(fact: dict[str, Any], section_purpose: str) -> CareerNarrativeClaim:
    fact_key = str(fact["fact_key"])
    conditional = bool(fact.get("conditional_language_required")) or float(fact.get("confidence", 1.0)) < 0.5
    if fact_key.startswith("contradiction:"):
        text = _mock_contradiction_text(fact)
    elif conditional:
        text = f"{section_purpose} Факт {fact_key} может проявляться, но вывод стоит проверить на реальных задачах."
    else:
        text = (
            f"{section_purpose} Факт {fact_key} описывает вероятный рабочий механизм, а не гарантированный результат."
        )
    return CareerNarrativeClaim(text=text, fact_keys=[fact_key], conditional=conditional)


def _mock_contradiction_text(fact: dict[str, Any]) -> str:
    dimension_phrases = {
        "leadership": "Лидерский потенциал может быть выражен",
        "autonomy": "Потенциал самостоятельной работы может быть выражен",
        "risk_tolerance": "Способность работать с риском и неопределённостью может быть выражена",
    }
    preference_phrases = {
        "people_management_motivation": "мотивация к управлению людьми может быть ниже",
        "autonomy_importance": "предпочтение структурированной работы может быть сильнее автономии",
        "risk_preference": "предпочтение стабильности может ограничивать готовность использовать риск",
    }
    dimension = dimension_phrases.get(str(fact.get("dimension")), "Профессиональная способность может быть выражена")
    preference = preference_phrases.get(
        str(fact.get("preference_key")), "пользовательское предпочтение может указывать на другой формат работы"
    )
    return f"{dimension}, но {preference}; поэтому сценарий стоит проверять в реальном контексте."


def _validate_claims(
    *,
    output: CareerSegmentOutput,
    section_input: CareerSectionRenderInput,
    allowed: set[str],
) -> None:
    body = _normalize_text(output.body)
    claimed = {fact_key for claim in output.claims for fact_key in claim.fact_keys}
    unknown = claimed - allowed
    if unknown:
        raise CareerNarrativeValidationError(f"unsupported claim facts: {sorted(unknown)}")
    missing = set(section_input.owned_fact_keys) - claimed
    if missing:
        raise CareerNarrativeValidationError(f"missing owned claim facts: {sorted(missing)}")
    if set(output.cited_fact_keys) != claimed:
        raise CareerNarrativeValidationError("claim citations mismatch")
    for claim in output.claims:
        if _normalize_text(claim.text) not in body:
            raise CareerNarrativeValidationError("claim text is not present in body")

    fact_index = {str(fact["fact_key"]): fact for fact in (*section_input.owned_facts, *section_input.reference_facts)}
    for fact_key, fact in fact_index.items():
        low_confidence = bool(fact.get("conditional_language_required")) or float(fact.get("confidence", 1.0)) < 0.5
        fact_claims = [claim for claim in output.claims if fact_key in claim.fact_keys]
        if low_confidence and (
            not fact_claims
            or any(not claim.conditional or not _has_conditional_language(claim.text) for claim in fact_claims)
        ):
            raise CareerNarrativeValidationError(f"low-confidence claim is categorical: {fact_key}")
        if fact_key.startswith("contradiction:") and not any(
            _retains_contradiction_meaning(claim.text, fact) for claim in fact_claims
        ):
            raise CareerNarrativeValidationError(f"contradiction meaning is missing: {fact_key}")


def _has_conditional_language(text: str) -> bool:
    normalized = _normalize_text(text)
    return any(
        marker in normalized
        for marker in (
            "может",
            "могут",
            "возможно",
            "вероятно",
            "скорее",
            "зависит",
            "стоит проверить",
            "требует проверки",
            "при условии",
        )
    )


def _retains_contradiction_meaning(text: str, fact: dict[str, Any]) -> bool:
    normalized = _normalize_text(text)
    dimension_markers = {
        "leadership": ("лидер", "влиян"),
        "autonomy": ("автоном", "самостоятель"),
        "risk_tolerance": ("риск", "неопредел"),
    }
    preference_markers = {
        "people_management_motivation": ("управлен", "люд", "команд"),
        "autonomy_importance": ("структур", "автоном", "самостоятель"),
        "risk_preference": ("стабил", "риск", "предсказ"),
    }
    contrast_markers = ("но", "однако", "при этом", "несмотря", "хотя")
    dimension = str(fact.get("dimension", ""))
    preference = str(fact.get("preference_key", ""))
    expected_dimension_markers = dimension_markers.get(dimension)
    expected_preference_markers = preference_markers.get(preference)
    return bool(
        expected_dimension_markers
        and expected_preference_markers
        and any(marker in normalized for marker in expected_dimension_markers)
        and any(marker in normalized for marker in expected_preference_markers)
        and any(marker in normalized for marker in contrast_markers)
    )


def _normalize_text(text: str) -> str:
    return " ".join(re.findall(r"[\w-]+", text.lower(), flags=re.UNICODE))


def _body_similarity(left: str, right: str) -> float:
    return SequenceMatcher(a=_normalize_text(left), b=_normalize_text(right), autojunk=False).ratio()


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
        output = validate_segment_output(output=CareerSegmentOutput.model_validate(raw), section_input=section_input)
        usage = estimate_provider_usage(
            prompt=prompt,
            output=output.model_dump_json(),
            input_cost_per_million=settings.CAREER_LLM_INPUT_COST_PER_MILLION,
            output_cost_per_million=settings.CAREER_LLM_OUTPUT_COST_PER_MILLION,
        )
        career_telemetry.record_provider_usage(
            input_tokens=int(usage["input_tokens"]),
            output_tokens=int(usage["output_tokens"]),
            cost_usd=float(usage["cost_usd"]),
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
    except (CareerNarrativeValidationError, ValidationError):
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
            error="career_validation_failure",
        )
    except Exception as exc:
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
            output_payload=_safe_provider_failure_payload(exc),
            error="career_provider_failure",
        )


def _safe_provider_failure_payload(exc: Exception) -> dict[str, Any]:
    """Keep a contract-safe failure summary so provider drift stays diagnosable.

    The provider error can carry a preview of the raw model answer; the generated prose never
    lands in the stored row, only the failure shape, so a repeated mismatch can be diagnosed
    without replaying the call.
    """

    details = str(exc)
    if "preview=" in details:
        details = details.split("preview=")[0].rstrip("; ")
    return {
        "error_code": str(getattr(exc, "code", "") or "career_provider_failure"),
        "error_type": type(exc).__name__,
        "details": details[:400],
    }


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


def assemble_career_report_row(*, report: CareerReport, segment_rows: list[CareerSegmentGeneration]) -> CareerReport:
    ready_sections: list[dict[str, Any]] = []
    seen_bodies: list[str] = []
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
        if any(_body_similarity(canonical_body, existing) >= 0.88 for existing in seen_bodies):
            raise CareerNarrativeValidationError("near-duplicate narrative section")
        seen_bodies.append(canonical_body)
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
        "top_dimensions",
        "low_dimensions",
        "career_archetypes",
        "preferred_environment",
        "risk_environment",
        "contradictions",
        "role_matches",
        "career_paths",
    ):
        keys.update(str(item["fact_key"]) for item in payload.get(name, []))
    return keys


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
