# ruff: noqa: RUF001
"""New-generation thematic ownership; historical V1-V3 remain frozen."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from app.modules.child.guidance_facts import ChildGuidanceFacts

# Source-topic x fact-family x destination. Measures are editorial inputs, not
# permission to promote a moderate score to a strength or invent a conflict.
INTERACTION_DESTINATIONS: Final = {
    "emotional_attunement": "natural_contact",
    "boundary_fit": "friction_zones",
    "tempo_fit": "friction_zones",
    "soothing_compatibility": "soothing_support",
    "communication_fit": "explanation_learning",
    "learning_interaction": "explanation_learning",
    "conflict_pattern": "conflict_cycle",
    "autonomy_balance": "not_personal",
}
OBSERVATION_DESTINATIONS: Final = {
    "soothing": "soothing_support",
    "boundaries": "boundaries_rules",
    "communication": "explanation_learning",
    "transitions": "conscious_adjustments",
    "autonomy": "autonomy",
    "current_age": "current_age",
}


def interaction_owned(fact: Mapping[str, Any], *, section_key: str, family: str) -> bool:
    if family == "source_profiles":
        return (
            fact.get("source_kind") == "interaction"
            and INTERACTION_DESTINATIONS.get(str(fact.get("dimension"))) == section_key
        )
    if family == "recommended_actions":
        return (
            OBSERVATION_DESTINATIONS.get(str(fact.get("topic")))
            or INTERACTION_DESTINATIONS.get(str(fact.get("dimension")))
        ) == section_key
    if family == "avoid_patterns":
        return INTERACTION_DESTINATIONS.get(str(fact.get("dimension"))) == section_key
    return False


def thematic_evidence_summary(facts: ChildGuidanceFacts, *, section_key: str) -> dict[str, str]:
    """Project distinct observation gaps and calculated signal strength for V5."""
    if section_key not in set(INTERACTION_DESTINATIONS.values()) | (
        set(OBSERVATION_DESTINATIONS.values()) - {"current_age"}
    ):
        return {}
    profiles = [
        item
        for item in facts.source_profiles
        if interaction_owned(item, section_key=section_key, family="source_profiles")
    ]
    actions = [
        item
        for item in facts.recommended_actions
        if interaction_owned(item, section_key=section_key, family="recommended_actions")
    ]
    missing = any(item["reason_code"] == "selected_observation_missing" for item in actions)
    if section_key not in INTERACTION_DESTINATIONS.values() and not missing:
        # A child-needs measure belongs here, but the interaction measure has a
        # different owner. Do not claim that the child-needs input is absent.
        return {}
    if not profiles and not actions:
        return {
            "evidence_state": "missing_data",
            "evidence_note": "Расчётного показателя и выбранного наблюдения по теме нет.",
        }
    states = {item["signal_state"] for item in profiles}
    directions = {
        "support" if float(item["score"]) >= 65 else "tension"
        for item in profiles
        if item["signal_state"] == "pronounced_signal"
    }
    if missing:
        state = "missing_data"
        note = "Не хватает выбранного наблюдения по теме; доступный расчётный ориентир не заменяет наблюдение."
    elif "ambiguous_signals" in states or len(directions) > 1:
        state = "ambiguous_signals"
        note = "Основания неоднозначны: уверенности недостаточно или расчётные сигналы направлены по-разному."
    elif "pronounced_signal" in states:
        state = "pronounced_signal"
        note = "Есть выраженный расчётный ориентир; его нужно проверить в повседневном контакте."
    elif states:
        state = "no_pronounced_skew"
        note = "Данные по теме есть, но в расчёте нет выраженного перекоса к опоре или напряжению."
    else:
        # Observation-based actions can exist without a calculated measure.
        state = "missing_data"
        note = "Расчётного показателя по теме нет; доступны только сохранённые наблюдения."
    return {"evidence_state": state, "evidence_note": note}


def approved_text_v4(
    family: str, fact: Mapping[str, Any], *, section_key: str, age_stage: str, first_owned: bool = False
) -> str:
    from app.modules.child.content_v3 import _INTERACTION_OBSERVATIONS, approved_text_v3
    from app.modules.child.narrative import _DIMENSION_LABELS

    if family == "source_profiles" and fact["source_kind"] == "interaction":
        dimension = str(fact["dimension"])
        score, confidence = float(fact["score"]), float(fact["confidence"])
        signal = (
            "основания неоднозначны: уверенности недостаточно для направленного вывода"
            if confidence < 0.4
            else "в данных нет выраженного перекоса к опоре или напряжению"
            if 35 < score < 65
            else "расчёт выделяет возможную опору, которую нужно проверить в контакте"
            if score >= 65
            else "расчёт выделяет возможное напряжение, но не устанавливает его причину"
        )
        limits = (
            {
                "natural_contact": "Этот показатель не доказывает, что контакт уже складывается легко. ",
                "friction_zones": "Здесь не установлена устойчивая зона трудностей. " if 35 < score < 65 else "",
                "conflict_cycle": (
                    "По этому показателю нельзя восстановить конкретный цикл конфликта или последовательность реакций. "
                ),
                "not_personal": (
                    "Расчёт баланса помощи не устанавливает намерения ребёнка "
                    "и не доказывает личную направленность реакции. "
                ),
            }.get(section_key, "")
            if first_owned
            else ""
        )
        qualifier = "Возможно, взрослый может" if confidence < 0.5 else "Взрослый может"
        return (
            f"{limits}Ориентир взаимодействия про {_DIMENSION_LABELS[dimension]}: {score:g} из 100, "
            f"уверенность {confidence:g}; {signal}. "
            f"{qualifier} наблюдать, {_INTERACTION_OBSERVATIONS[dimension]}."
        )
    return approved_text_v3(family, fact, section_key=section_key, age_stage=age_stage, first_owned=first_owned)
