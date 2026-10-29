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
from app.modules.child.guidance_facts import (
    GUIDANCE_FACTS_CONTRACT_V2,
    LOW_CONFIDENCE_THRESHOLD,
    SOURCE_PROFILE_CONTRACT_VERSIONS,
    ChildGuidanceFacts,
)
from app.modules.child.prompts.v1 import SECTION_METADATA, build_child_section_prompt
from app.modules.child.quality import fact_matches_section, guidance_prompt_content, section_contracts
from app.modules.child.safety import ChildSafetyViolation, NarrativeSectionCandidate, validate_child_narrative
from app.modules.llm.exceptions import LLMTimeoutError

CHILD_PROMPT_VERSION: Final = "child-section-prompt-v1"
CURRENT_CHILD_PROMPT_VERSION: Final = "child-section-prompt-v3"
_PROMPT_VERSIONS: Final = {
    "child_section_render_input_v1": CHILD_PROMPT_VERSION,
    "child_section_render_input_v2": "child-section-prompt-v2",
    "child_section_render_input_v3": CURRENT_CHILD_PROMPT_VERSION,
}
_INPUT_VERSIONS: Final = {
    "child-guidance-facts-v1": "child_section_render_input_v1",
    GUIDANCE_FACTS_CONTRACT_V2: "child_section_render_input_v2",
    "child-guidance-facts-v3": "child_section_render_input_v3",
}
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


def prompt_version_for_input(section_input: ChildSectionRenderInput) -> str:
    return _PROMPT_VERSIONS[section_input.contract_version]


def _provider_usage_is_valid(value: object) -> bool:
    """Validate optional v3 accounting before publication, total over hostile JSON."""
    if not isinstance(value, dict):
        return False
    counters = {"http_attempts", "responses_with_usage", "responses_without_usage"}
    tokens = {"prompt_tokens", "completion_tokens", "total_tokens"}
    cache = {"prompt_cache_hit_tokens", "prompt_cache_miss_tokens"}
    if not counters <= value.keys() or value.keys() - (counters | tokens | cache):
        return False
    if any(type(number) is not int or not 0 <= number <= 2**63 - 1 for number in value.values()):
        return False
    if value["responses_with_usage"] + value["responses_without_usage"] > value["http_attempts"]:
        return False
    if value["responses_with_usage"] == 0:
        return value.keys() == counters  # No measured tokens is not measured zero tokens.
    if not tokens <= value.keys() or value["total_tokens"] != value["prompt_tokens"] + value["completion_tokens"]:
        return False
    if cache.intersection(value):
        return (
            cache <= value.keys()
            and value["prompt_cache_hit_tokens"] + value["prompt_cache_miss_tokens"] == value["prompt_tokens"]
        )
    return True


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

    contract_version: Literal[
        "child_section_render_input_v1", "child_section_render_input_v2", "child_section_render_input_v3"
    ]
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


def _ordered_families(families: frozenset[str], *, version: str) -> tuple[str, ...]:
    # v2 introduces multi-family sections: set iteration would change local IDs
    # and persisted prompt/input hashes across worker interpreter restarts.
    return tuple(sorted(families)) if version in SOURCE_PROFILE_CONTRACT_VERSIONS else tuple(families)


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


_PROFILE_LABELS = {
    "emotional_responsiveness": "эмоциональная отзывчивость взрослого",
    "structure": "структура, предлагаемая взрослым",
    "control_tendency": "контроль со стороны взрослого",
    "flexibility": "гибкость взрослого",
    "communication_style": "стиль объяснения взрослого",
    "protection": "защита и поддержка взрослого",
    "autonomy_support": "поддержка самостоятельности взрослым",
    "consistency": "последовательность взрослого",
    "reassurance": "поддержка и ободрение",
    "predictability": "предсказуемость",
    "autonomy": "самостоятельность",
    "verbal_explanation": "словесные объяснения",
    "physical_sensory_calm": "спокойная сенсорная обстановка",
    "exploration": "исследование нового",
    "recognition": "похвала и признание усилий",
    "personal_space": "личное пространство",
    "transition_time": "время на переходы",
    "variety": "разнообразие",
}


_PROFILE_SCALE_CONTEXT = {
    # Russian renderings of the pinned scale poles, not new recommendations.
    "emotional_responsiveness": (
        "Шкала сопоставляет сдержанный отклик взрослого и более быстрый эмоциональный отклик с ободрением."
    ),
    "structure": (
        "Шкала идёт от более свободной организации к явно заданному распорядку и правилам; "
        "высокий показатель не означает лучшего воспитания."
    ),
    "control_tendency": (
        "Шкала различает менее директивное участие и стремление взрослого удерживать управление; "
        "ни один полюс не является оценкой качества родительства."
    ),
    "flexibility": "Шкала сопоставляет приверженность плану и адаптацию взрослого к изменению темпа и обстоятельств.",
    "communication_style": (
        "Шкала различает краткое объяснение через действие и более подробный словесный диалог взрослого."
    ),
    "protection": "Шкала сопоставляет наблюдение с дистанции и готовность взрослого активно защищать и вмешиваться.",
    "autonomy_support": (
        "Шкала различает близкое сопровождение взрослого и предоставление выбора с поддержкой самостоятельных попыток."
    ),
    "consistency": (
        "Шкала сопоставляет изменяющийся по обстоятельствам отклик взрослого "
        "и более повторяемый, устойчивый порядок действий."
    ),
    "reassurance": (
        "Шкала различает спокойную доступность взрослого и более частое явное эмоциональное ободрение в контакте."
    ),
    "predictability": (
        "Шкала сопоставляет спонтанный ход общения и устойчивый распорядок с заранее понятными ожиданиями."
    ),
    "autonomy": (
        "Шкала различает совместные решения с близкой помощью взрослого и значимый выбор с самостоятельными попытками."
    ),
    "verbal_explanation": (
        "Шкала сопоставляет короткие подсказки и показ на примере с подробным объяснением и диалогом."
    ),
    "physical_sensory_calm": (
        "Шкала различает более интенсивную стимуляцию и контакт в спокойной обстановке с меньшей сенсорной нагрузкой."
    ),
    "exploration": "Шкала сопоставляет знакомый путь с сопровождением и пространство для исследования и проб.",
    "recognition": (
        "Шкала различает меньшую потребность в явной обратной связи и ясное признание усилий и вклада; "
        "это не мера способностей и не требование заслуживать одобрение."
    ),
    "personal_space": (
        "Шкала сопоставляет непрерывное совместное участие и защищённое личное пространство для восстановления."
    ),
    "transition_time": "Шкала различает быстрые переключения и постепенные переходы с предварительным предупреждением.",
    "variety": "Шкала сопоставляет повторение в устойчивом ритме и разнообразие занятий и подходов.",
}


def _profile_text(fact: Mapping[str, Any], *, section_key: str) -> str:
    kind = str(fact["source_kind"])
    dimension = str(fact["dimension"])
    label = _DIMENSION_LABELS[dimension] if kind == "interaction" else _PROFILE_LABELS[dimension]
    source = {
        "parent_style": "стиля взрослого",
        "child_needs": "возможных потребностей в контакте",
        "interaction": "взаимодействия",
    }[kind]
    score, confidence = float(fact["score"]), float(fact["confidence"])
    if section_key == "parent_strengths":
        return (
            f"Возможно, взрослый может проверить как ресурс собственную сторону взаимодействия: {label}. "
            "Расчёт стиля взрослого выделяет эту сторону, но не доказывает, что она помогает конкретному ребёнку. "
            f"{_PROFILE_SCALE_CONTEXT[dimension]} "
            "Опору имеет смысл считать рабочей только после сопоставления с реальным контактом, а не по одному расчёту."
        )
    uncertainty = (
        "Оснований для направленного вывода недостаточно."
        if confidence < 0.4
        else "Расчёт находится между полюсами шкалы и не даёт оснований выбрать один способ как устойчиво подходящий."
        if 35 < score < 65
        else "Это расчётная гипотеза, а не подтверждённое наблюдение."
    )
    scale_context = _PROFILE_SCALE_CONTEXT.get(dimension, "") if kind != "interaction" else ""
    if confidence >= 0.4 and not 35 < score < 65:
        pole = "второй" if score >= 65 else "первый"
        uncertainty = f"В расчётной модели заметнее {pole} полюс; это гипотеза для проверки, не наблюдаемый факт."
    return (
        f"Возможно, взрослый может использовать расчёт {source} как вопрос для наблюдения: {label}. "
        f"{scale_context} {uncertainty} "
        "Это не оценка способностей и не фиксированная черта ребёнка; сопоставляйте гипотезу с повседневным контактом."
    )


_TOPIC_CONTEXT = {
    "soothing": "поддержки и успокоения",
    "boundaries": "границ и правил",
    "communication": "объяснений взрослого",
    "transitions": "смены занятий и темпа переходов",
    "autonomy": "помощи и самостоятельности",
    "current_age": "текущего возрастного этапа",
}
_REASON_CONTEXT = {
    "selected_observation_missing": "Для этой темы нет выбранного наблюдения; вывод пока делать нельзя.",
    "observed_context_is_variable": "Наблюдения зависят от обстоятельств; один эпизод нельзя считать правилом.",
    "evidence_not_directionally_conclusive": (
        "Расчёт и наблюдение не дают однозначного основания для направленного вывода."
    ),
    "observation_confirms_interaction_expectation": (
        "Наблюдение согласуется с расчётной гипотезой, но не устанавливает постоянную черту."
    ),
    "observation_opposes_interaction_expectation": (
        "Наблюдение расходится с расчётной гипотезой; ориентир нужно проверять в реальном контакте."
    ),
    "interaction_above_strength_threshold": (
        "Расчёт показывает возможную опору для контакта, а не доказанный навык взрослого."
    ),
    "interaction_below_friction_threshold": "Расчёт выделяет возможное напряжение, а не вину ребёнка или взрослого.",
    "friction_requires_conscious_adult_adjustment": (
        "Расчёт предлагает проверить реакцию взрослого в этой зоне напряжения."
    ),
}


_AGE_STAGE_LABELS = {
    "0-1": "до одного года",
    "1-3": "от 1 до 3 лет",
    "3-6": "от 3 до 6 лет",
    "6-9": "от 6 до 9 лет",
    "9-12": "от 9 до 12 лет",
    "12-15": "от 12 до 15 лет",
    "15-18": "от 15 до 18 лет",
}
_UNCERTAINTY_TOPIC_ACTIONS = {
    "soothing": (
        "сначала наблюдать, как ребёнок возвращается к спокойствию "
        "и что предшествует этому, до выбора способа поддержки",
        "отмечать, в каких обстоятельствах один и тот же способ поддержки сопровождается разной реакцией ребёнка",
        "проверить небольшое изменение привычного способа поддержки "
        "и наблюдать, как ребёнок возвращается к спокойствию",
    ),
    "boundaries": (
        "сначала наблюдать реакцию на объяснение правила, прежде чем выбирать способ его предъявления",
        "сопоставлять обстоятельства разных реакций на одно правило, не считая отдельный протест постоянным свойством",
        "проверить небольшое изменение в формулировке правила и наблюдать, как меняется реакция при его объяснении",
    ),
    "communication": (
        "сначала наблюдать, как собственный способ объяснения соотносится с пониманием ребёнка",
        "отмечать, когда привычное объяснение оказывается понятным, а когда требуется уточнение",
        "проверить небольшое изменение способа объяснения и наблюдать, что ребёнок понял и что нужно уточнить",
    ),
    "transitions": (
        "сначала наблюдать, как проходит смена занятий и в какой момент возникает затруднение",
        "сопоставлять условия лёгких и трудных переключений, не делая вывод по одной смене занятия",
        "проверить небольшое изменение подготовки к смене занятия и наблюдать, как проходит переключение",
    ),
    "autonomy": (
        "сначала наблюдать, как ребёнок участвует в посильном деле с помощью взрослого и без неё",
        "отмечать, при каких условиях ребёнок просит помощь, а при каких пробует сам, не превращая это в ярлык",
        "проверить небольшое изменение в объёме помощи в посильном деле и наблюдать, как меняется участие ребёнка",
    ),
}
_UNCERTAINTY_ACTION_INDEX = {
    "adult_observes_before_choosing_guidance": 0,
    "adult_tracks_context_before_generalizing": 1,
    "adult_tests_small_adjustment_and_observes": 2,
}


def _current_approved_text(family: str, fact: Mapping[str, Any], *, section_key: str, age_stage: str) -> str:
    if family == "source_profiles":
        return _profile_text(fact, section_key=section_key)
    if section_key == "how_to_use":
        return (
            "Взрослый может читать этот отчёт как набор проверяемых ориентиров, а не описание характера ребёнка. "
            f"Рекомендации привязаны к возрастному этапу {_AGE_STAGE_LABELS[age_stage]}; "
            "не переносите их на другие этапы автоматически. "
            "Различайте расчётные гипотезы, наблюдения и неопределённость; "
            "отсутствие раздела не означает отсутствие потребности."
        )
    if family == "strong_matches":
        dimension = _DIMENSION_LABELS[str(fact["dimension"])]
        return (
            f"Взрослый может проверить возможную опору для контакта: {dimension}. "
            "Расчёт взаимодействия выделяет здесь совпадение; это не доказательство наблюдаемого успеха. "
            "Ориентируйтесь на то, поддерживает ли такой способ реальное общение."
        )
    if family == "friction_points":
        dimension = _DIMENSION_LABELS[str(fact["dimension"])]
        return (
            f"Взрослый может внимательнее наблюдать {dimension}. "
            "Расчёт взаимодействия отмечает возможное напряжение, а не свойство ребёнка или вину взрослого. "
            "Проверяйте, в каких обстоятельствах возникает трудность, прежде чем делать устойчивый вывод."
        )
    text = _approved_text(family, fact)
    action_code = str(fact.get("action_code"))
    if action_code == "adult_reuses_working_interaction_pattern":
        dimension = _DIMENSION_LABELS[str(fact["dimension"])]
        return (
            "Если в повседневном контакте способ помогает, взрослый может спокойно повторять его, "
            f"проверяя {dimension}. "
            "Расчёт выделяет возможную опору, но не устанавливает, что этот способ уже проверен в вашей семье."
        )
    if family == "recommended_actions" and action_code in _UNCERTAINTY_ACTION_INDEX:
        action = _UNCERTAINTY_TOPIC_ACTIONS[str(fact["topic"])][_UNCERTAINTY_ACTION_INDEX[action_code]]
        prefix = (
            "Возможно, взрослый может" if float(fact["confidence"]) < LOW_CONFIDENCE_THRESHOLD else "Взрослый может"
        )
        return f"{prefix} {action}. {_REASON_CONTEXT[str(fact['reason_code'])]}"
    context = _TOPIC_CONTEXT.get(str(fact.get("topic"))) or _DIMENSION_LABELS.get(str(fact.get("dimension")))
    reason = _REASON_CONTEXT.get(str(fact.get("reason_code")), "")
    if context:
        text = f"В теме {context}: {text}"
    if reason:
        text = f"{text} {reason}"
    return text


def _section_fact(
    *,
    local_id: str,
    family: str,
    fact: Mapping[str, Any],
    section_key: str = "",
    version: str = "",
    age_stage: str = "",
) -> ChildSectionFact:
    confidence = float(fact["confidence"])
    if version == "child-guidance-facts-v3":
        from app.modules.child.content_v3 import approved_text_v3

        text = approved_text_v3(
            family, fact, section_key=section_key, age_stage=age_stage, first_owned=local_id == "owned-1"
        )
    elif version == GUIDANCE_FACTS_CONTRACT_V2:
        text = _current_approved_text(family, fact, section_key=section_key, age_stage=age_stage)
    else:
        text = _approved_text(family, fact)
    return ChildSectionFact(
        id=local_id,
        family=family,
        approved_text=text,
        conditional=confidence < LOW_CONFIDENCE_THRESHOLD,
    )


def _family_facts(payload: Mapping[str, Any], family: str) -> list[dict[str, Any]]:
    value = payload.get(family, [])
    return [dict(fact) for fact in value if isinstance(fact, Mapping)]


def build_child_section_inputs(guidance_facts: ChildGuidanceFacts) -> list[ChildSectionRenderInput]:
    """Project validated Guidance Facts into minimal, content-only provider inputs."""

    payload = guidance_prompt_content(guidance_facts)
    inputs: list[ChildSectionRenderInput] = []
    for section_key, contract in section_contracts(guidance_facts.contract_version).items():
        title, purpose = SECTION_METADATA[section_key]
        owned_raw = [
            (family, raw)
            for family in _ordered_families(contract.owned_fact_families, version=guidance_facts.contract_version)
            for raw in _family_facts(payload, family)
            if fact_matches_section(
                raw, section_key=section_key, version=guidance_facts.contract_version, contract=contract, family=family
            )
        ]
        reference_raw = [
            (family, raw)
            for family in _ordered_families(contract.reference_fact_families, version=guidance_facts.contract_version)
            for raw in _family_facts(payload, family)
        ]
        owned = [
            _section_fact(
                local_id=f"owned-{index}",
                family=family,
                fact=fact,
                section_key=section_key,
                version=guidance_facts.contract_version,
                age_stage=guidance_facts.age_stage,
            )
            for index, (family, fact) in enumerate(owned_raw, start=1)
        ]
        references = [
            _section_fact(
                local_id=f"reference-{index}",
                family=family,
                fact=fact,
                section_key=section_key,
                version=guidance_facts.contract_version,
                age_stage=guidance_facts.age_stage,
            )
            for index, (family, fact) in enumerate(reference_raw, start=1)
        ]
        inputs.append(
            ChildSectionRenderInput(
                contract_version=_INPUT_VERSIONS[guidance_facts.contract_version],
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
    contract = section_contracts(guidance_facts.contract_version)[section_key]
    owned = [
        str(raw["id"])
        for family in _ordered_families(contract.owned_fact_families, version=guidance_facts.contract_version)
        for raw in _family_facts(payload, family)
        if fact_matches_section(
            raw, section_key=section_key, version=guidance_facts.contract_version, contract=contract, family=family
        )
    ]
    references = [
        str(raw["id"])
        for family in _ordered_families(contract.reference_fact_families, version=guidance_facts.contract_version)
        for raw in _family_facts(payload, family)
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
    prompt_version: str | None = None,
    artifact_generation_id: UUID | None = None,
) -> models.ChildSegmentGeneration:
    """Build a durable provider-call intent before the external side effect."""

    canonical = _canonical_section_input(
        guidance_facts=guidance_facts,
        section_key=section_input.section_key,
    )
    if section_input != canonical or not canonical.owned_facts:
        raise ChildNarrativeValidationError("provider intent requires a canonical non-empty section")
    expected_version = prompt_version_for_input(canonical)
    if prompt_version is not None and prompt_version != expected_version:
        raise ChildNarrativeValidationError("prompt version does not match stored content contract")
    prompt_version = expected_version
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
    prompt_version: str | None = None,
    artifact_generation_id: UUID | None = None,
) -> models.ChildSegmentGeneration:
    """Generate one independently retryable section and return a persistable row."""

    canonical = _canonical_section_input(guidance_facts=guidance_facts, section_key=section_input.section_key)
    if section_input != canonical:
        raise ChildNarrativeValidationError("section input is not canonical")
    expected_version = prompt_version_for_input(canonical)
    if prompt_version is not None and prompt_version != expected_version:
        raise ChildNarrativeValidationError("prompt version does not match stored content contract")
    prompt_version = expected_version
    provider_name, model_name = _provider_identity(provider)
    prompt = build_child_section_prompt(canonical)
    input_payload = canonical.model_dump(mode="json")
    prompt_hash = _stable_hash({"prompt": prompt})
    input_hash = _stable_hash(input_payload)
    base_diagnostics: dict[str, Any] = {
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
        if canonical.contract_version == "child_section_render_input_v3":
            from app.modules.llm.usage import capture_provider_usage

            with capture_provider_usage() as usage:
                try:
                    raw = await provider.generate_segment(prompt=prompt, section_input=canonical)
                finally:
                    # Include observed attempts on failures too; missing token
                    # usage stays absent, never a fabricated zero-token result.
                    base_diagnostics["provider_usage"] = usage.to_payload()
        else:
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
