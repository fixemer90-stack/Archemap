# ruff: noqa: RUF001
"""Bounded modular LLM narrative pipeline for Child Report."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any, Final, Literal, Protocol, cast
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.modules.child import models
from app.modules.child.guidance_facts import LOW_CONFIDENCE_THRESHOLD, ChildGuidanceFacts
from app.modules.child.prompts.v1 import SECTION_METADATA, build_child_section_prompt
from app.modules.child.quality import SECTION_CONTRACTS, SectionContract, guidance_prompt_content
from app.modules.child.safety import ChildSafetyViolation, NarrativeSectionCandidate, validate_child_narrative
from app.modules.llm.exceptions import LLMTimeoutError

CHILD_PROMPT_VERSION: Final = "child-section-prompt-v1"
CHILD_SECTION_INPUT_VERSION: Final = "child_section_render_input_v1"
CHILD_SEGMENT_OUTPUT_VERSION: Final = "child_segment_output_v1"
_DIMENSION_LABELS: Final = {
    "emotional_attunement": "эмоциональную настроенность",
    "boundary_fit": "способ задавать границы",
    "soothing_compatibility": "способ поддержки и успокоения",
    "communication_fit": "способ объяснять",
    "autonomy_balance": "баланс помощи и самостоятельности",
    "learning_interaction": "способ сопровождать обучение",
    "conflict_pattern": "поведение взрослого в конфликте",
    "tempo_fit": "темп взаимодействия",
}
_ACTION_TEXT: Final = {
    "adult_reuses_working_interaction_pattern": "спокойно повторять уже работающий способ контакта",
    "adult_slows_down_and_observes_response": "замедлиться и сначала наблюдать за ответом ребёнка",
    "adult_uses_nonautomatic_supportive_response": "выбрать поддерживающую реакцию вместо автоматической",
    "adult_observes_before_choosing_guidance": "сначала понаблюдать и только затем выбирать рекомендацию",
    "adult_tracks_context_before_generalizing": "отслеживать контекст и не делать вывод по одному эпизоду",
    "adult_tests_small_adjustment_and_observes": "проверить небольшое изменение и наблюдать за результатом",
    "continue_observed_soothing_support": "продолжать тот способ успокоения, который помогает в наблюдениях",
    "test_observed_soothing_before_escalating": "проверить другой способ поддержки до усиления воздействия",
    "continue_calm_clear_boundaries": "сохранять спокойные и понятные границы",
    "reduce_pressure_and_explain_before_conflict": "снизить давление и объяснить правило до развития конфликта",
    "use_clear_age_appropriate_explanations": "давать ясные объяснения, подходящие текущему возрасту",
    "vary_explanation_length_and_check_understanding": "менять длину объяснения и проверять понимание",
    "prepare_transitions_calmly": "заранее и спокойно готовить ребёнка к переходам",
    "add_transition_warning_and_processing_time": "предупреждать о переходе и оставлять время на перестройку",
    "offer_age_appropriate_choice": "предлагать ограниченный выбор, подходящий возрасту",
    "calibrate_choice_without_forcing_independence": "настраивать объём выбора без принуждения к самостоятельности",
    "adult_provides_coregulation_and_predictable_rhythm": "поддерживать совместную регуляцию и предсказуемый ритм",
    "adult_prepares_transitions_and_offers_bounded_choice": "готовить к переходам и предлагать ограниченный выбор",
    "adult_names_emotions_and_uses_playful_clear_limits": (
        "называть эмоции и задавать ясные границы через спокойную игру"
    ),
    "adult_explains_rules_and_supports_practice_after_mistakes": (
        "объяснять правила и помогать тренироваться после ошибок"
    ),
    "adult_combines_structure_with_growing_responsibility": "сочетать понятную структуру с растущей ответственностью",
    "adult_respects_privacy_and_keeps_calm_availability": (
        "уважать личное пространство и сохранять спокойную доступность"
    ),
    "adult_negotiates_responsibility_and_preserves_safe_limits": (
        "обсуждать ответственность и сохранять безопасные границы"
    ),
}
_AVOID_TEXT: Final = {
    "dismiss_child_signals": "обесценивать сигналы ребёнка",
    "escalate_pressure_during_boundary_protest": "усиливать давление во время протеста против границ",
    "repeat_soothing_that_increases_distress": "повторять способ успокоения, который усиливает напряжение",
    "overload_with_explanations_during_conflict": "перегружать объяснениями во время конфликта",
    "interpret_independence_as_disobedience": "считать стремление к самостоятельности непослушанием",
    "correct_before_checking_understanding": "исправлять до проверки понимания",
    "mirror_child_escalation": "отвечать усилением на усиление реакции ребёнка",
    "expect_behavior_above_current_age_stage": "ожидать поведения выше текущего возрастного этапа",
    "escalate_without_observation": "усиливать воздействие без предварительного наблюдения",
}
_ALLOWED_PROVIDER_NAMES: Final = frozenset({"mock", "openrouter", "deepseek", "disabled"})
_MODEL_REFERENCE_PATTERN: Final = re.compile(r"model-sha256:[0-9a-f]{64}")
_ERROR_TYPES: Final = frozenset({"validation_error", "provider_error"})


def _provider_name_is_valid(value: object) -> bool:
    return type(value) is str and value in _ALLOWED_PROVIDER_NAMES


def _model_name_is_valid(value: object) -> bool:
    return type(value) is str and _MODEL_REFERENCE_PATTERN.fullmatch(value) is not None


def _model_reference(value: object) -> str:
    if type(value) is not str or not value or len(value) > 200 or any(ord(character) < 32 for character in value):
        raise ValueError("model name is invalid")
    if _model_name_is_valid(value):
        return value
    return f"model-sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _error_type_is_valid(value: object) -> bool:
    return type(value) is str and value in _ERROR_TYPES


class ChildNarrativeValidationError(ValueError):
    """Raised when one generated section violates its bounded contract."""


class ChildSectionFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    family: str
    approved_text: str
    conditional: bool


class ChildSectionRenderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["child_section_render_input_v1"]
    section_key: str
    section_title: str
    section_purpose: str
    owned_facts: list[ChildSectionFact]
    reference_facts: list[ChildSectionFact]
    retry_scope: Literal["same_section_only"]
    maximum_attempts: int = Field(ge=1, le=2)

    @property
    def owned_fact_ids(self) -> tuple[str, ...]:
        return tuple(fact.id for fact in self.owned_facts)

    @property
    def allowed_fact_ids(self) -> frozenset[str]:
        return frozenset(fact.id for fact in (*self.owned_facts, *self.reference_facts))


class ChildNarrativeClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    fact_ids: list[str] = Field(min_length=1, max_length=1)
    conditional: bool


class ChildSegmentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["child_segment_output_v1"]
    section_key: str
    title: str
    body: str = Field(min_length=1)
    cited_fact_ids: list[str] = Field(min_length=1)
    claims: list[ChildNarrativeClaim] = Field(min_length=1)


class ChildSegmentProvider(Protocol):
    provider_name: str
    model_name: str

    async def generate_segment(
        self,
        *,
        prompt: str,
        section_input: ChildSectionRenderInput,
    ) -> dict[str, Any]: ...


class StructuredChildProvider(Protocol):
    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: Any,
        schema: type[ChildSegmentOutput],
    ) -> ChildSegmentOutput: ...


class StructuredChildSegmentProviderAdapter:
    def __init__(self, *, provider: StructuredChildProvider, provider_name: str, model_name: str) -> None:
        if not _provider_name_is_valid(provider_name):
            raise ValueError("provider and model names are required")
        self._provider = provider
        self.provider_name = provider_name
        self.model_name = _model_reference(model_name)

    async def generate_segment(
        self,
        *,
        prompt: str,
        section_input: ChildSectionRenderInput,
    ) -> dict[str, Any]:
        response = await self._provider.generate_structured(
            prompt=prompt,
            narrative_input=cast(Any, section_input),
            schema=ChildSegmentOutput,
        )
        return response.model_dump(mode="json")


class DisabledChildSegmentProvider:
    """Controlled production provider used when narrative generation is disabled."""

    provider_name = "disabled"
    model_name = _model_reference("child-narrative-disabled-v1")

    async def generate_segment(
        self,
        *,
        prompt: str,
        section_input: ChildSectionRenderInput,
    ) -> dict[str, Any]:
        del prompt, section_input
        raise RuntimeError("child narrative provider is disabled")


class MockChildSegmentProvider:
    provider_name = "mock"
    model_name = _model_reference("child-contract-mock-v1")

    async def generate_segment(
        self,
        *,
        prompt: str,
        section_input: ChildSectionRenderInput,
    ) -> dict[str, Any]:
        del prompt
        claims = [
            ChildNarrativeClaim(text=fact.approved_text, fact_ids=[fact.id], conditional=fact.conditional)
            for fact in section_input.owned_facts
        ]
        return ChildSegmentOutput(
            contract_version=CHILD_SEGMENT_OUTPUT_VERSION,
            section_key=section_input.section_key,
            title=section_input.section_title,
            body=" ".join(claim.text for claim in claims),
            cited_fact_ids=[fact.id for fact in section_input.owned_facts],
            claims=claims,
        ).model_dump(mode="json")


def _matches_owned_scope(fact: Mapping[str, Any], *, contract: SectionContract) -> bool:
    if not contract.owned_topics and not contract.owned_dimensions:
        return True
    return fact.get("topic") in contract.owned_topics or fact.get("dimension") in contract.owned_dimensions


def _approved_text(family: str, fact: Mapping[str, Any]) -> str:
    confidence = float(fact["confidence"])
    prefix = "Возможно, взрослый может" if confidence < LOW_CONFIDENCE_THRESHOLD else "Взрослый может"
    if family == "strong_matches":
        dimension = _DIMENSION_LABELS[str(fact["dimension"])]
        return f"{prefix} опираться на {dimension}, который уже поддерживает контакт."
    if family == "friction_points":
        dimension = _DIMENSION_LABELS[str(fact["dimension"])]
        return f"{prefix} внимательнее проверять {dimension}, потому что здесь вероятно напряжение."
    if family == "avoid_patterns":
        return f"{prefix} избегать действия: {_AVOID_TEXT[str(fact['pattern_code'])]}."
    action = _ACTION_TEXT[str(fact["action_code"])]
    return f"{prefix} {action}."


def _section_fact(*, local_id: str, family: str, fact: Mapping[str, Any]) -> ChildSectionFact:
    confidence = float(fact["confidence"])
    return ChildSectionFact(
        id=local_id,
        family=family,
        approved_text=_approved_text(family, fact),
        conditional=confidence < LOW_CONFIDENCE_THRESHOLD,
    )


def _family_facts(payload: Mapping[str, Any], family: str) -> list[dict[str, Any]]:
    value = payload.get(family, [])
    return [dict(fact) for fact in value if isinstance(fact, Mapping)]


def build_child_section_inputs(guidance_facts: ChildGuidanceFacts) -> list[ChildSectionRenderInput]:
    """Project validated Guidance Facts into minimal, content-only provider inputs."""

    payload = guidance_prompt_content(guidance_facts)
    inputs: list[ChildSectionRenderInput] = []
    for section_key, contract in SECTION_CONTRACTS.items():
        title, purpose = SECTION_METADATA[section_key]
        owned_raw = [
            (family, raw)
            for family in contract.owned_fact_families
            for raw in _family_facts(payload, family)
            if _matches_owned_scope(raw, contract=contract)
        ]
        reference_raw = [
            (family, raw) for family in contract.reference_fact_families for raw in _family_facts(payload, family)
        ]
        owned = [
            _section_fact(local_id=f"owned-{index}", family=family, fact=fact)
            for index, (family, fact) in enumerate(owned_raw, start=1)
        ]
        references = [
            _section_fact(local_id=f"reference-{index}", family=family, fact=fact)
            for index, (family, fact) in enumerate(reference_raw, start=1)
        ]
        inputs.append(
            ChildSectionRenderInput(
                contract_version=CHILD_SECTION_INPUT_VERSION,
                section_key=section_key,
                section_title=title,
                section_purpose=purpose,
                owned_facts=owned,
                reference_facts=references,
                retry_scope="same_section_only",
                maximum_attempts=2,
            )
        )
    return inputs


def _canonical_section_input(*, guidance_facts: ChildGuidanceFacts, section_key: str) -> ChildSectionRenderInput:
    try:
        return next(item for item in build_child_section_inputs(guidance_facts) if item.section_key == section_key)
    except StopIteration as exc:
        raise ChildNarrativeValidationError("unknown section") from exc


def _section_fact_id_map(*, guidance_facts: ChildGuidanceFacts, section_key: str) -> dict[str, str]:
    payload = guidance_prompt_content(guidance_facts)
    contract = SECTION_CONTRACTS[section_key]
    owned = [
        str(raw["id"])
        for family in contract.owned_fact_families
        for raw in _family_facts(payload, family)
        if _matches_owned_scope(raw, contract=contract)
    ]
    references = [
        str(raw["id"]) for family in contract.reference_fact_families for raw in _family_facts(payload, family)
    ]
    return {
        **{f"owned-{index}": fact_id for index, fact_id in enumerate(owned, start=1)},
        **{f"reference-{index}": fact_id for index, fact_id in enumerate(references, start=1)},
    }


def validate_segment_output(
    *,
    output: ChildSegmentOutput,
    section_input: ChildSectionRenderInput,
    guidance_facts: ChildGuidanceFacts,
) -> ChildSegmentOutput:
    canonical = _canonical_section_input(guidance_facts=guidance_facts, section_key=section_input.section_key)
    if section_input != canonical:
        raise ChildNarrativeValidationError("section input is not canonical")
    if output.section_key != section_input.section_key or output.title != section_input.section_title:
        raise ChildNarrativeValidationError("section mismatch")
    claim_ids = [claim.fact_ids[0] for claim in output.claims]
    if output.cited_fact_ids != claim_ids or len(claim_ids) != len(set(claim_ids)):
        raise ChildNarrativeValidationError("claims and cited facts differ")
    cited = set(output.cited_fact_ids)
    unsupported = cited - section_input.allowed_fact_ids
    if unsupported:
        raise ChildNarrativeValidationError(f"unsupported facts: {sorted(unsupported)}")
    missing_owned = set(section_input.owned_fact_ids) - cited
    if missing_owned:
        raise ChildNarrativeValidationError(f"missing owned facts: {sorted(missing_owned)}")

    approved = {fact.id: fact for fact in (*section_input.owned_facts, *section_input.reference_facts)}
    for claim in output.claims:
        fact = approved[claim.fact_ids[0]]
        if claim.text != fact.approved_text or claim.conditional is not fact.conditional:
            raise ChildNarrativeValidationError("claim is not the approved fact rendering")
    if output.body != " ".join(claim.text for claim in output.claims):
        raise ChildNarrativeValidationError("body is not fully covered by claims")

    try:
        fact_id_map = _section_fact_id_map(
            guidance_facts=guidance_facts,
            section_key=section_input.section_key,
        )
        validate_child_narrative(
            NarrativeSectionCandidate(
                section_key=output.section_key,
                content=output.body,
                fact_refs=tuple(fact_id_map[reference] for reference in output.cited_fact_ids),
            ),
            guidance_facts=guidance_facts,
        )
    except ChildSafetyViolation as exc:
        raise ChildNarrativeValidationError(f"child safety violation: {','.join(exc.categories)}") from exc
    return output


def _provider_identity(provider: ChildSegmentProvider) -> tuple[str, str]:
    provider_name = getattr(provider, "provider_name", None)
    model_name = getattr(provider, "model_name", None)
    if not _provider_name_is_valid(provider_name):
        raise ChildNarrativeValidationError("provider name is required")
    if not _model_name_is_valid(model_name):
        raise ChildNarrativeValidationError("model name is required")
    return cast(str, provider_name), cast(str, model_name)


def _segment_row(
    *,
    guidance_facts: ChildGuidanceFacts,
    section_input: ChildSectionRenderInput,
    status: str,
    prompt_version: str,
    model_name: str,
    content: str | None,
    evidence_refs: list[str],
    error_code: str | None,
    diagnostics: dict[str, Any],
    lifecycle_token: UUID | None = None,
    artifact_generation_id: UUID | None = None,
) -> models.ChildSegmentGeneration:
    return models.ChildSegmentGeneration(
        child_profile_id=guidance_facts.child_id,
        generation_id=artifact_generation_id or guidance_facts.generation_id,
        section_key=section_input.section_key,
        status=status,
        prompt_version=prompt_version,
        model=model_name,
        content=content,
        evidence_refs=evidence_refs,
        error_code=error_code,
        lifecycle_token=lifecycle_token,
        diagnostics=diagnostics,
    )


def build_child_segment_intent(
    *,
    provider: ChildSegmentProvider,
    section_input: ChildSectionRenderInput,
    guidance_facts: ChildGuidanceFacts,
    lifecycle_token: UUID,
    prompt_version: str = CHILD_PROMPT_VERSION,
    artifact_generation_id: UUID | None = None,
) -> models.ChildSegmentGeneration:
    """Build a durable provider-call intent before the external side effect."""

    canonical = _canonical_section_input(
        guidance_facts=guidance_facts,
        section_key=section_input.section_key,
    )
    if section_input != canonical or not canonical.owned_facts:
        raise ChildNarrativeValidationError("provider intent requires a canonical non-empty section")
    provider_name, model_name = _provider_identity(provider)
    prompt = build_child_section_prompt(canonical)
    return _segment_row(
        guidance_facts=guidance_facts,
        section_input=canonical,
        status="in_progress",
        prompt_version=prompt_version,
        model_name=model_name,
        content=None,
        evidence_refs=[],
        error_code=None,
        lifecycle_token=lifecycle_token,
        artifact_generation_id=artifact_generation_id,
        diagnostics={
            "provider": provider_name,
            "model": model_name,
            "prompt_version": prompt_version,
            "retry_scope": canonical.retry_scope,
            "prompt_hash": _stable_hash({"prompt": prompt}),
            "input_hash": _stable_hash(canonical.model_dump(mode="json")),
            "attempts": 0,
        },
    )


async def run_child_segment_generation(
    *,
    provider: ChildSegmentProvider,
    section_input: ChildSectionRenderInput,
    guidance_facts: ChildGuidanceFacts,
    prompt_version: str = CHILD_PROMPT_VERSION,
    artifact_generation_id: UUID | None = None,
) -> models.ChildSegmentGeneration:
    """Generate one independently retryable section and return a persistable row."""

    canonical = _canonical_section_input(guidance_facts=guidance_facts, section_key=section_input.section_key)
    if section_input != canonical:
        raise ChildNarrativeValidationError("section input is not canonical")
    provider_name, model_name = _provider_identity(provider)
    prompt = build_child_section_prompt(canonical)
    input_payload = canonical.model_dump(mode="json")
    prompt_hash = _stable_hash({"prompt": prompt})
    input_hash = _stable_hash(input_payload)
    base_diagnostics = {
        "provider": provider_name,
        "model": model_name,
        "prompt_version": prompt_version,
        "retry_scope": canonical.retry_scope,
        "prompt_hash": prompt_hash,
        "input_hash": input_hash,
    }
    if not canonical.owned_facts:
        return _segment_row(
            guidance_facts=guidance_facts,
            section_input=canonical,
            status="not_applicable",
            prompt_version=prompt_version,
            model_name=model_name,
            content=None,
            evidence_refs=[],
            error_code=None,
            diagnostics=base_diagnostics | {"attempts": 0, "reason": "no_owned_facts"},
            artifact_generation_id=artifact_generation_id,
        )

    if isinstance(provider, DisabledChildSegmentProvider):
        return _segment_row(
            guidance_facts=guidance_facts,
            section_input=canonical,
            status="failed",
            prompt_version=prompt_version,
            model_name=model_name,
            content=None,
            evidence_refs=[],
            error_code="child_narrative_disabled",
            diagnostics=base_diagnostics | {"attempts": 0, "error_type": "provider_error"},
            artifact_generation_id=artifact_generation_id,
        )

    try:
        raw = await provider.generate_segment(prompt=prompt, section_input=canonical)
        parsed = ChildSegmentOutput.model_validate(raw)
        output = validate_segment_output(
            output=parsed,
            section_input=canonical,
            guidance_facts=guidance_facts,
        )
        output_payload = output.model_dump(mode="json")
        return _segment_row(
            guidance_facts=guidance_facts,
            section_input=canonical,
            status="ready",
            prompt_version=prompt_version,
            model_name=model_name,
            content=output.body,
            evidence_refs=[
                _section_fact_id_map(
                    guidance_facts=guidance_facts,
                    section_key=canonical.section_key,
                )[reference]
                for reference in output.cited_fact_ids
            ],
            error_code=None,
            diagnostics=base_diagnostics
            | {"attempts": 1, "output_hash": _stable_hash(output_payload), "output": output_payload},
            artifact_generation_id=artifact_generation_id,
        )
    except (ChildNarrativeValidationError, ValidationError):
        error_code = "child_narrative_validation_failure"
        error_type = "validation_error"
    except Exception as exc:  # fail closed without storing provider text
        # Adapters wrap HTTP transport failures. A response may have been lost
        # after remote acceptance, so neither automatic nor manual recall is safe.
        cause: BaseException | None = exc
        seen: set[int] = set()
        ambiguous = False
        while cause is not None and id(cause) not in seen:
            seen.add(id(cause))
            if isinstance(cause, (LLMTimeoutError, TimeoutError, httpx.TransportError)):
                ambiguous = True
                break
            cause = cause.__cause__ or cause.__context__
        error_code = "child_narrative_provider_outcome_unknown" if ambiguous else "child_narrative_provider_failure"
        error_type = "provider_error"

    return _segment_row(
        guidance_facts=guidance_facts,
        section_input=canonical,
        status="failed",
        prompt_version=prompt_version,
        model_name=model_name,
        content=None,
        evidence_refs=[],
        error_code=error_code,
        diagnostics=base_diagnostics | {"attempts": 1, "error_type": error_type},
        artifact_generation_id=artifact_generation_id,
    )


def _stable_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
