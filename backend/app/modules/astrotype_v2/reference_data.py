"""Canonical Astrotype v2 reference data seed builders."""

# ruff: noqa: RUF001

from __future__ import annotations

from dataclasses import dataclass

from app.modules.astrotype_v2 import models

CANONICAL_BODY_ORDER: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "North Node",
    "Chiron",
)
_BODY_ORDER_INDEX = {body: index for index, body in enumerate(CANONICAL_BODY_ORDER)}


def canonicalize_body_pair(body_a: str, body_b: str) -> tuple[str, str]:
    """Return a stable canonical order for symmetric v2 body-pair reference keys."""
    keyed = sorted((body_a, body_b), key=lambda body: (_BODY_ORDER_INDEX.get(body, 10_000), body))
    return keyed[0], keyed[1]


@dataclass(frozen=True, slots=True)
class AspectDefinitionSeed:
    """Seed data for one canonical v2 aspect type."""

    code: str
    name: str
    angle_degrees: float
    default_orb_degrees: float
    major: bool
    sort_order: int
    description: str


@dataclass(frozen=True, slots=True)
class AspectPairInterpretationSeed:
    """Seed data for one versioned v2 aspect pair interpretation."""

    aspect_code: str
    planet_a: str
    planet_b: str
    locale: str
    summary: str
    keywords: tuple[str, ...]
    source_version: str
    enabled: bool


CANONICAL_ASPECT_DEFINITIONS: tuple[AspectDefinitionSeed, ...] = (
    AspectDefinitionSeed(
        code="conjunction",
        name="Conjunction",
        angle_degrees=0.0,
        default_orb_degrees=8.0,
        major=True,
        sort_order=10,
        description="Bodies operate in a merged field of attention and emphasis.",
    ),
    AspectDefinitionSeed(
        code="sextile",
        name="Sextile",
        angle_degrees=60.0,
        default_orb_degrees=4.0,
        major=True,
        sort_order=20,
        description="Bodies cooperate through available skills, choices and constructive openings.",
    ),
    AspectDefinitionSeed(
        code="square",
        name="Square",
        angle_degrees=90.0,
        default_orb_degrees=6.0,
        major=True,
        sort_order=30,
        description="Bodies create friction that demands action, adjustment and embodied resolution.",
    ),
    AspectDefinitionSeed(
        code="trine",
        name="Trine",
        angle_degrees=120.0,
        default_orb_degrees=6.0,
        major=True,
        sort_order=40,
        description="Bodies flow together through familiar talents, ease and integrated capacity.",
    ),
    AspectDefinitionSeed(
        code="quincunx",
        name="Quincunx",
        angle_degrees=150.0,
        default_orb_degrees=3.0,
        major=False,
        sort_order=50,
        description="Bodies require ongoing recalibration between unlike needs or operating modes.",
    ),
    AspectDefinitionSeed(
        code="opposition",
        name="Opposition",
        angle_degrees=180.0,
        default_orb_degrees=8.0,
        major=True,
        sort_order=60,
        description="Bodies polarize awareness across two poles that must be held in conscious balance.",
    ),
)


CANONICAL_ASPECT_PAIR_INTERPRETATIONS: tuple[AspectPairInterpretationSeed, ...] = (
    AspectPairInterpretationSeed(
        aspect_code="sextile",
        planet_a="Mercury",
        planet_b="Saturn",
        locale="ru",
        summary=(
            "Меркурий в секстиле к Сатурну связывает мышление с дисциплиной: идеи легче превращаются "
            "в структуру, план и проверяемые выводы."
        ),
        keywords=("мышление", "дисциплина", "структура", "планирование"),
        source_version="v2.0",
        enabled=True,
    ),
    AspectPairInterpretationSeed(
        aspect_code="opposition",
        planet_a="Mars",
        planet_b="Uranus",
        locale="ru",
        summary=(
            "Марс в оппозиции к Урану показывает напряжение между импульсом действия и потребностью "
            "в свободе, требуя осознанного канала для резких разворотов энергии."
        ),
        keywords=("действие", "свобода", "напряжение", "прорыв"),
        source_version="v2.0",
        enabled=True,
    ),
)


def build_aspect_definition_rows() -> list[models.AspectDefinition]:
    """Build v2 ORM rows for canonical aspect type definitions without persisting them."""
    return [
        models.AspectDefinition(
            code=seed.code,
            name=seed.name,
            angle_degrees=seed.angle_degrees,
            default_orb_degrees=seed.default_orb_degrees,
            major=seed.major,
            sort_order=seed.sort_order,
            description=seed.description,
        )
        for seed in CANONICAL_ASPECT_DEFINITIONS
    ]


def build_aspect_pair_interpretation_rows() -> list[models.AspectPairInterpretation]:
    """Build v2 ORM rows for canonical aspect pair examples without persisting them."""
    return [
        models.AspectPairInterpretation(
            aspect_code=seed.aspect_code,
            planet_a=seed.planet_a,
            planet_b=seed.planet_b,
            locale=seed.locale,
            summary=seed.summary,
            keywords=list(seed.keywords),
            source_version=seed.source_version,
            enabled=seed.enabled,
        )
        for seed in CANONICAL_ASPECT_PAIR_INTERPRETATIONS
    ]
