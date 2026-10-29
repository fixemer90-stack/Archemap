# ruff: noqa: RUF001
"""Generation-time v3 composition: shared method once, local evidence in each claim.

This is not a read-time rewrite. v1/v2 renderers remain pinned in narrative.py.
Observation questions unpack the bounded dimension; they do not assert behaviour
or prescribe a new intervention beyond the registered caregiver action.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

# Each question operationalizes the *specific* source dimension. No rotation of
# equivalent generic advice and no provider-authored unsupported bridge prose.
_PROFILE_OBSERVATIONS: Final = {
    "emotional_responsiveness": "как быстро взрослый замечает эмоциональный сигнал и отвечает на него",
    "structure": "насколько явно взрослый задаёт распорядок и объясняет правила",
    "control_tendency": "когда взрослый удерживает управление, а когда оставляет пространство для инициативы",
    "flexibility": "как взрослый меняет план при изменении темпа или обстоятельств",
    "communication_style": "когда взрослый показывает действие, а когда разворачивает словесное объяснение",
    "protection": "в каких ситуациях взрослый наблюдает с дистанции, а в каких активно вмешивается для поддержки",
    "autonomy_support": "сколько помощи взрослый оставляет при выборе и самостоятельной попытке",
    "consistency": "что в отклике взрослого повторяется, а что меняется вместе с обстоятельствами",
    "reassurance": "как соотносятся спокойная доступность и явное ободрение в повседневном контакте",
    "predictability": "как проходит контакт при спонтанном ходе событий и при заранее понятном распорядке",
    "autonomy": "как ребёнок участвует в совместном решении и в посильной самостоятельной попытке",
    "verbal_explanation": "что становится понятным после короткой подсказки, показа или подробного диалога",
    "physical_sensory_calm": "как меняется контакт вместе с интенсивностью окружающей сенсорной нагрузки",
    "exploration": "как проходит знакомое действие с сопровождением и проба нового",
    "recognition": "как ребёнок откликается на явное признание усилий и на менее выраженную обратную связь",
    "personal_space": "как соотносятся совместное участие и пространство для восстановления",
    "transition_time": "как проходит быстрое переключение и переход с предварительным предупреждением",
    "variety": "как складывается участие при повторении и при разнообразии занятий",
}
_INTERACTION_OBSERVATIONS: Final = {
    "emotional_attunement": "как эмоциональный отклик взрослого соотносится с сигналами ребёнка",
    "boundary_fit": "как предлагаемые взрослым правила соотносятся с реакцией на границы",
    "soothing_compatibility": "как способ поддержки взрослого соотносится с возвращением к спокойствию",
    "communication_fit": "как способ объяснения взрослого соотносится с пониманием в диалоге",
    "autonomy_balance": "как объём помощи взрослого соотносится с самостоятельным участием ребёнка",
    "learning_interaction": "как сопровождение взрослого соотносится с пробами и уточнением после ошибок",
    "conflict_pattern": "как реакция взрослого соотносится с усилением или ослаблением напряжения в конфликте",
    "tempo_fit": "как темп взрослого соотносится со временем, нужным для переключения",
}


def approved_text_v3(
    family: str, fact: Mapping[str, Any], *, section_key: str, age_stage: str, first_owned: bool = False
) -> str:
    # Imported lazily because the frozen v1/v2 catalogs are owned by narrative.
    from app.modules.child.narrative import (
        _ACTION_TEXT,
        _AGE_STAGE_LABELS,
        _AVOID_TEXT,
        _DIMENSION_LABELS,
        _PROFILE_LABELS,
        _PROFILE_SCALE_CONTEXT,
        _TOPIC_CONTEXT,
        _UNCERTAINTY_ACTION_INDEX,
        _UNCERTAINTY_TOPIC_ACTIONS,
    )

    if section_key == "how_to_use":
        return (
            "Взрослый может читать этот отчёт как набор проверяемых ориентиров, а не описание характера ребёнка. "
            f"Рекомендации привязаны к возрастному этапу {_AGE_STAGE_LABELS[age_stage]}. "
            "Это не оценка способностей и не фиксированная черта ребёнка; "
            "сопоставляйте гипотезу с повседневным контактом. "
            "Шкалы стиля взрослого описывают его сторону контакта, шкалы потребностей — возможные условия контакта, "
            "а расчёт взаимодействия сопоставляет обе стороны; это не подтверждённые наблюдения. "
            "Отметка «между полюсами» не выбирает устойчиво подходящий способ; "
            "«недостаточно оснований» не позволяет делать направленный вывод даже при крайнем значении шкалы. "
            "В расчёте взаимодействия высокий полюс обозначает возможную опору, низкий — возможное напряжение. "
            "При отсутствии наблюдения сначала наблюдайте, при изменчивых реакциях сопоставляйте обстоятельства, "
            "при неоднозначных основаниях проверяйте только небольшое изменение. "
            "Не переносите рекомендации на другие возрастные этапы автоматически; "
            "отсутствие раздела не означает отсутствие потребности."
        )

    confidence = float(fact["confidence"])
    prefix = "Возможно, взрослый может" if confidence < 0.5 else "Взрослый может"
    dimension = str(fact.get("dimension"))
    if family == "source_profiles":
        kind = str(fact["source_kind"])
        score = float(fact["score"])
        label = _DIMENSION_LABELS[dimension] if kind == "interaction" else _PROFILE_LABELS[dimension]
        question = (_INTERACTION_OBSERVATIONS if kind == "interaction" else _PROFILE_OBSERVATIONS)[dimension]
        perspective = {
            "parent_style": "стиля взрослого",
            "child_needs": "возможных потребностей в контакте",
            "interaction": "взаимодействия",
        }[kind]
        # The local marker always survives: report-wide explanation must never
        # launder a confident-sounding assertion from uncertain evidence.
        state = (
            "недостаточно оснований для направления"
            if confidence < 0.4
            else "между полюсами"
            if 35 < score < 65
            else "предположительно второй полюс"
            if score >= 65
            else "предположительно первый полюс"
        )
        if section_key == "parent_strengths":
            scope_note = "Выделение ресурса в расчёте не доказывает успеха в семье. " if first_owned else ""
            return (
                f"{scope_note}Как возможный ресурс взрослого выделена сторона: {label}. "
                f"{prefix} проверить её пользу именно в контакте с ребёнком, наблюдая, {question}."
            )
        scale = f" {_PROFILE_SCALE_CONTEXT[dimension]}" if kind != "interaction" else ""
        introduction = (
            {
                "parent_style": (
                    "Взрослый может исследовать свою сторону контакта по этим шкалам, не приписывая её ребёнку. "
                ),
                "child_interaction_needs": (
                    "Взрослый может проверить предполагаемые условия контакта по отклику ребёнка. "
                ),
                "praise_recognition": (
                    "Взрослый может наблюдать отклик на признание усилий, не оценивая личность ребёнка. "
                ),
                "soothing_support": "Взрослый может замечать условия возвращения к спокойствию. ",
                "boundaries_rules": "Взрослый может наблюдать, как воспринимается предсказуемый порядок. ",
                "autonomy": "Взрослый может сопоставлять участие с помощью и самостоятельные попытки. ",
                "explanation_learning": "Взрослый может проверять понимание при разных способах объяснения. ",
                "conscious_adjustments": "Взрослый может различать темп переходов и отдельные стороны взаимодействия. ",
            }.get(section_key, "")
            if first_owned
            else ""
        )
        qualifier = "Возможно, ориентир" if confidence < 0.5 else "Ориентир"
        return (
            f"{introduction}{qualifier} расчёта {perspective}: {label} — {state}.{scale} "
            f"Вопрос для наблюдения: {question}?"
        )

    if family in {"strong_matches", "friction_points"}:
        signal = "возможную опору" if family == "strong_matches" else "возможное напряжение"
        return f"{prefix} проверить {signal} в контакте, наблюдая, {_INTERACTION_OBSERVATIONS[dimension]}."
    if family == "avoid_patterns":
        return f"{prefix} избегать действия: {_AVOID_TEXT[str(fact['pattern_code'])]}."

    if family == "compensation_areas":
        return (
            f"В зоне осознанной настройки {prefix.lower()} выбрать поддерживающую реакцию вместо автоматической; "
            f"ориентир для проверки — {_INTERACTION_OBSERVATIONS[dimension]}."
        )

    code = str(fact["action_code"])
    if code in _UNCERTAINTY_ACTION_INDEX:
        action = _UNCERTAINTY_TOPIC_ACTIONS[str(fact["topic"])][_UNCERTAINTY_ACTION_INDEX[code]]
        condition = {
            "adult_observes_before_choosing_guidance": "Пока нет выбранного наблюдения",
            "adult_tracks_context_before_generalizing": "Если реакция меняется с обстоятельствами",
            "adult_tests_small_adjustment_and_observes": "При неоднозначных основаниях",
        }[code]
        return f"{condition}, {prefix.lower()} {action}."
    if code == "adult_reuses_working_interaction_pattern":
        return (
            f"Если способ помогает в повседневном контакте, {prefix.lower()} повторять его, "
            f"сопоставляя, {_INTERACTION_OBSERVATIONS[dimension]}."
        )
    context = _TOPIC_CONTEXT.get(str(fact.get("topic"))) or _DIMENSION_LABELS.get(dimension)
    action = _ACTION_TEXT[code]
    return f"В теме {context}: {prefix} {action}." if context else f"{prefix} {action}."
