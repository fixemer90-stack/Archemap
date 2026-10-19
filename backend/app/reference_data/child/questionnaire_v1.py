"""Versioned, backend-owned Child Report questionnaire catalog."""
# ruff: noqa: RUF001

from __future__ import annotations

from app.modules.child.age_resolver import AgeStage
from app.modules.child.questionnaire import (
    AnswerKind,
    Question,
    QuestionCategory,
    QuestionOption,
)

ALL_AGE_STAGES: tuple[AgeStage, ...] = ("0-1", "1-3", "3-6", "6-9", "9-12", "12-15", "15-18")
YOUNGER_STAGES: tuple[AgeStage, ...] = ("0-1", "1-3", "3-6", "6-9", "9-12")
CHOICE_STAGES: tuple[AgeStage, ...] = ("3-6", "6-9", "9-12", "12-15", "15-18")
SCHEDULE_STAGES: tuple[AgeStage, ...] = ("6-9", "9-12", "12-15", "15-18")


def _options(*pairs: tuple[str, str]) -> tuple[QuestionOption, ...]:
    return tuple(QuestionOption(code=code, label_ru=label) for code, label in pairs)


QUESTION_CATALOG: tuple[Question, ...] = (
    Question(
        key="caregiver_daily_contact",
        prompt_ru="Как часто вы обычно проводите время с ребёнком?",
        category=QuestionCategory.CAREGIVER_CONTEXT,
        answer_kind=AnswerKind.SINGLE_CHOICE,
        options=_options(("high", "Каждый день"), ("medium", "Несколько раз в неделю"), ("limited", "Реже")),
        required=True,
        age_stages=ALL_AGE_STAGES,
    ),
    Question(
        key="caregiver_boundary_role",
        prompt_ru="Кто чаще помогает ребёнку соблюдать правила?",
        category=QuestionCategory.CAREGIVER_CONTEXT,
        answer_kind=AnswerKind.SINGLE_CHOICE,
        options=_options(
            ("mostly_me", "Чаще я"), ("shared", "Обычно вместе"), ("mostly_other", "Чаще другой взрослый")
        ),
        required=True,
        age_stages=ALL_AGE_STAGES,
    ),
    Question(
        key="observation_soothing",
        prompt_ru="Что чаще помогает, когда ребёнок сильно расстроен?",
        category=QuestionCategory.OBSERVATION,
        answer_kind=AnswerKind.SINGLE_CHOICE,
        options=_options(
            ("physical_contact", "Спокойный физический контакт"),
            ("talk", "Разговор"),
            ("quiet_presence", "Молча побыть рядом"),
            ("switch_attention", "Мягко переключить внимание"),
            ("space", "Дать пространство"),
            ("depends", "Зависит от ситуации"),
        ),
        required=True,
        age_stages=ALL_AGE_STAGES,
    ),
    Question(
        key="observation_boundary_reaction",
        prompt_ru="Что чаще происходит после спокойного и понятного ограничения?",
        category=QuestionCategory.OBSERVATION,
        answer_kind=AnswerKind.SINGLE_CHOICE,
        options=_options(
            ("accepts_calmly", "Обычно принимает"),
            ("accepts_with_explanation", "Принимает после объяснения"),
            ("protests", "Протестует"),
            ("withdraws", "Замыкается"),
            ("depends", "Зависит от ситуации"),
        ),
        required=True,
        age_stages=ALL_AGE_STAGES,
    ),
    Question(
        key="parent_preference_explanation",
        prompt_ru="Как вам удобнее объяснять новое ребёнку?",
        category=QuestionCategory.PARENT_PREFERENCE,
        answer_kind=AnswerKind.SINGLE_CHOICE,
        options=_options(
            ("short", "Коротко"), ("detailed", "Подробно"), ("show", "Показать на примере"), ("depends", "По ситуации")
        ),
        required=True,
        age_stages=ALL_AGE_STAGES,
    ),
    Question(
        key="family_constraint_routine",
        prompt_ru="Насколько семье обычно удаётся сохранять предсказуемый распорядок?",
        category=QuestionCategory.FAMILY_CONSTRAINT,
        answer_kind=AnswerKind.SINGLE_CHOICE,
        options=_options(
            ("stable", "Обычно удаётся"),
            ("variable", "Часто меняется"),
            ("limited", "Сейчас это трудно"),
            ("depends", "По ситуации"),
        ),
        required=True,
        age_stages=ALL_AGE_STAGES,
    ),
    Question(
        key="observation_transition",
        prompt_ru="Как обычно проходят переходы между занятиями?",
        category=QuestionCategory.OBSERVATION,
        answer_kind=AnswerKind.SINGLE_CHOICE,
        options=_options(
            ("easy", "Обычно спокойно"),
            ("warning_helps", "Помогает предупреждение"),
            ("hard", "Часто трудно"),
            ("depends", "По ситуации"),
        ),
        required=True,
        age_stages=YOUNGER_STAGES,
    ),
    Question(
        key="observation_autonomy",
        prompt_ru="Как часто ребёнок стремится сделать доступные по возрасту вещи самостоятельно?",
        category=QuestionCategory.OBSERVATION,
        answer_kind=AnswerKind.SINGLE_CHOICE,
        options=_options(("rarely", "Редко"), ("sometimes", "Иногда"), ("often", "Часто"), ("depends", "По ситуации")),
        required=True,
        age_stages=ALL_AGE_STAGES,
    ),
    Question(
        key="parent_preference_choice",
        prompt_ru="Какой способ дать выбор вам проще использовать?",
        category=QuestionCategory.PARENT_PREFERENCE,
        answer_kind=AnswerKind.SINGLE_CHOICE,
        options=_options(
            ("two_choices", "Два приемлемых варианта"),
            ("open_choice", "Открытый выбор"),
            ("adult_decides", "Решение взрослого"),
            ("depends", "По ситуации"),
        ),
        required=True,
        age_stages=CHOICE_STAGES,
    ),
    Question(
        key="family_constraint_schedule",
        prompt_ru="Насколько семейный график позволяет заранее предупреждать об изменениях?",
        category=QuestionCategory.FAMILY_CONSTRAINT,
        answer_kind=AnswerKind.SINGLE_CHOICE,
        options=_options(
            ("usually", "Обычно позволяет"), ("sometimes", "Иногда"), ("rarely", "Редко"), ("depends", "По ситуации")
        ),
        required=True,
        age_stages=SCHEDULE_STAGES,
    ),
)

ANSWER_COMPATIBILITY: dict[tuple[str, str], frozenset[str]] = {}
