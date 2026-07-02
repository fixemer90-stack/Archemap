# ruff: noqa: RUF001
"""Human storytelling contract for Self report tone and readability."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.report_narratives.exceptions import NarrativeValidationError

HUMAN_STORYTELLING_CONTRACT_VERSION = "self_human_storytelling_v1"
HUMAN_STORYTELLING_CHAIN = (
    "recognition",
    "personal_formula",
    "lived_scene",
    "inner_tension",
    "protective_strategy",
    "mature_expression",
    "soft_question",
)


@dataclass(frozen=True)
class HumanToneGuide:
    """Product tone rules for humanized Self storytelling."""

    hero_rule: str
    evidence_rule: str
    minimum_unit: tuple[str, ...]


@dataclass(frozen=True)
class HumanToneBannedPattern:
    """A dry/generic tone pattern that should be repaired before display."""

    code: str
    label: str
    markers: tuple[str, ...]
    rewrite_hint: str


@dataclass(frozen=True)
class HumanToneExample:
    """Before/after example for the tone guide."""

    section_id: str
    before: str
    after: str
    evidence_handling: str = "secondary_progressive_disclosure"


HUMAN_TONE_GUIDE = HumanToneGuide(
    hero_rule=(
        "Hero must be recognition-first: start with a human reading of the lived pattern, "
        "not raw placements, socionics labels, scores, or calculation-first evidence."
    ),
    evidence_rule=(
        "evidence remains source of truth, but it should be progressively disclosed after the user-facing "
        "meaning instead of interrupting the first emotional read."
    ),
    minimum_unit=HUMAN_STORYTELLING_CHAIN,
)

HUMAN_TONE_BANNED_PATTERNS = (
    HumanToneBannedPattern(
        code="bureaucratic_abstraction",
        label="Канцелярит и служебная абстракция",
        markers=(
            "формирует паттерн",
            "формируют паттерн",
            "эмоциональная обработка",
            "эмоциональной обработки",
            "внутренняя динамика",
            "внутренней динамики",
            "механизм проявляется",
            "данная конфигурация",
        ),
        rewrite_hint="Переписать через конкретное жизненное проявление, напряжение, защиту и зрелую форму.",
    ),
    HumanToneBannedPattern(
        code="generic_astrology_prose",
        label="Generic astrology prose",
        markers=(
            "как и многие люди с такой картой",
            "типичный представитель",
            "энергии планет говорят",
            "звёзды показывают",
        ),
        rewrite_hint="Убрать гороскопический шаблон и назвать конкретную человеческую ситуацию.",
    ),
    HumanToneBannedPattern(
        code="unsupported_therapy_language",
        label="Unsupported therapy language",
        markers=(
            "травма",
            "исцелить внутреннего ребёнка",
            "диагностический профиль",
            "психотерапевтическая коррекция",
        ),
        rewrite_hint="Оставить мягкий психологический язык без диагноза, лечения и терапевтических обещаний.",
    ),
    HumanToneBannedPattern(
        code="technical_first_hero",
        label="Technical-first hero",
        markers=(
            "солнце в",
            "луна в",
            "асцендент в",
            "соционический тип",
            "уверенность расчёта",
        ),
        rewrite_hint=(
            "Начать hero с узнавания и личной формулы; вынести расчётные основания во вторичный evidence layer."
        ),
    ),
)

HUMAN_TONE_BEFORE_AFTER_EXAMPLES = (
    HumanToneExample(
        section_id="hero",
        before="Солнце и Луна в Козероге в 7 доме формируют устойчивый паттерн самоопределения.",
        after=(
            "Вам важно не просто быть собой в вакууме — вы точнее собираетесь рядом с другим человеком. "
            "В диалоге быстрее становится понятно, где ваша позиция, за что вы отвечаете и какие отношения "
            "выдерживают реальность, а не только эмоцию момента."
        ),
    ),
    HumanToneExample(
        section_id="main_formula",
        before="Доминанты карты формируют механизм ответственности и структурирования опыта.",
        after=(
            "Ваша главная формула — не торопиться с красивым впечатлением, а собрать опору, которой можно "
            "доверять. Когда внутри появляется ясный каркас, вы становитесь спокойнее, точнее и заметно сильнее."
        ),
    ),
    HumanToneExample(
        section_id="emotions_and_communication",
        before="Эмоциональная обработка проходит через аналитический фильтр и коммуникативную динамику.",
        after=(
            "Сильное чувство у вас редко остаётся просто волной. Почти сразу появляется попытка назвать его, "
            "объяснить, найти правильную форму — и именно здесь можно как прояснить контакт, так и слишком быстро "
            "закрыться в контроле."
        ),
    ),
    HumanToneExample(
        section_id="relationships",
        before="Партнёрская сфера активирует сценарии глубины, границ и взаимной регуляции.",
        after=(
            "В близости вам мало формальной симпатии. Нужен контакт, где можно почувствовать глубину, но не потерять "
            "собственные границы; поэтому вы можете одновременно тянуться к человеку и проверять, "
            "выдержит ли он реальность."
        ),
    ),
    HumanToneExample(
        section_id="development",
        before="Вектор развития связан с интеграцией зрелой формы и снижением защитных реакций.",
        after=(
            "Рост начинается там, где вы не заставляете себя сразу быть сильнее, а замечаете момент защиты. "
            "Если выдержать паузу и выбрать следующий спокойный шаг, внутренняя строгость превращается не в зажим, "
            "а в устойчивость."
        ),
    ),
)

_LIVED_MANIFESTATION_MARKERS = (
    "в диалоге",
    "в близости",
    "рядом с",
    "когда",
    "если",
    "снаружи",
    "в отношениях",
    "в напряжении",
    "следующий шаг",
    "пауза",
)


def validate_human_storytelling_text(text: str, *, location: str) -> list[NarrativeValidationError]:
    """Validate a user-facing prose fragment against the E15 human tone contract."""
    lowered = text.lower()
    errors: list[NarrativeValidationError] = []
    for pattern in HUMAN_TONE_BANNED_PATTERNS:
        if any(marker in lowered for marker in pattern.markers):
            errors.append(
                NarrativeValidationError(
                    code=pattern.code,
                    message=f"Human storytelling tone violation: {pattern.label}.",
                    location=location,
                    recoverable=True,
                )
            )
    if not any(marker in lowered for marker in _LIVED_MANIFESTATION_MARKERS):
        errors.append(
            NarrativeValidationError(
                code="missing_lived_manifestation",
                message="Human storytelling prose should include a concrete lived manifestation.",
                location=location,
                recoverable=True,
            )
        )
    return errors
