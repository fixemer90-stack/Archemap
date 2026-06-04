# ruff: noqa: RUF001
"""NarrativeInput builder for deterministic reports."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.modules.report_narratives.schemas import (
    ArchetypeSummary,
    AspectFact,
    AstroFact,
    CalculationQuality,
    EvidenceBackedClaim,
    NarrativeInput,
    NarrativeProfile,
    ProductBoundaries,
    SocionicsSummary,
)

PLANET_RU = {
    "Sun": "Солнце",
    "Moon": "Луна",
    "Mercury": "Меркурий",
    "Venus": "Венера",
    "Mars": "Марс",
    "Jupiter": "Юпитер",
    "Saturn": "Сатурн",
    "Uranus": "Уран",
    "Neptune": "Нептун",
    "Pluto": "Плутон",
}

SIGN_RU = {
    "Aries": "Овне",
    "Taurus": "Тельце",
    "Gemini": "Близнецах",
    "Cancer": "Раке",
    "Leo": "Льве",
    "Virgo": "Деве",
    "Libra": "Весах",
    "Scorpio": "Скорпионе",
    "Sagittarius": "Стрельце",
    "Capricorn": "Козероге",
    "Aquarius": "Водолее",
    "Pisces": "Рыбах",
}

ASPECT_RU = {
    "conjunction": "соединение",
    "opposition": "оппозиция",
    "trine": "тригон",
    "square": "квадрат",
    "sextile": "секстиль",
    "quincunx": "квинконс",
}

SELF_ALLOWED_SECTIONS = [
    "main_formula",
    "world_perception",
    "emotions_and_communication",
    "strengths",
    "vulnerabilities",
    "relationships",
    "sexuality",
    "development",
]

SECTION_MAP = {
    "strengths": "strengths",
    "risks": "risks",
    "relationships": "relationship_patterns",
    "sexuality": "sexuality_patterns",
    "development": "development_recommendations",
}


def build_narrative_input(report: Any) -> NarrativeInput:
    """Build curated NarrativeInput from deterministic report data."""
    report_data = report.report_data or {}
    profile_data = report_data.get("profile", {})
    chart = report_data.get("chart", {})
    claims = report_data.get("claims", [])

    narrative_profile = NarrativeProfile(
        name=profile_data.get("name", "Пользователь"),
        birth_date=_parse_birth_date(profile_data.get("birth_date")),
        birth_time_quality=profile_data.get("birth_time_quality", "unknown"),
        birth_place=profile_data.get("birth_place", "Неизвестно"),
    )

    calculation_quality = CalculationQuality(
        has_exact_birth_time=narrative_profile.birth_time_quality == "exact",
        has_known_birth_time=narrative_profile.birth_time_quality != "unknown",
        quality_label=_quality_label(narrative_profile.birth_time_quality),
        warning=report_data.get("quality_warning"),
    )

    key_facts = [
        _planet_fact(planet) for planet in chart.get("planets", []) if planet.get("name") and planet.get("sign")
    ]
    key_aspects = [
        _aspect_fact(aspect) for aspect in chart.get("aspects", []) if aspect.get("planet_a") and aspect.get("planet_b")
    ]

    grouped_claims = _group_claims(claims)

    socionics_data = report_data.get("socionics") or {}
    socionics = SocionicsSummary(
        type=socionics_data.get("type", "unknown"),
        type_ru=socionics_data.get("type_ru", "Не определено"),
        confidence_label=socionics_data.get("confidence_label", "не определена"),
        explanation=socionics_data.get(
            "explanation",
            "Детерминированный соционический вывод пока недоступен.",
        ),
    )

    archetype_data = report_data.get("archetype") or {}
    archetype = ArchetypeSummary(
        primary=archetype_data.get("primary", "Не определено"),
        confidence_label=(archetype_data.get("confidence") or {}).get(
            "label",
            "не определена",
        ),
        explanation=archetype_data.get(
            "explanation",
            "Архетипическое резюме будет уточнено на следующем этапе.",
        ),
    )

    return NarrativeInput(
        product=report.product,
        language="ru",
        profile=narrative_profile,
        calculation_quality=calculation_quality,
        key_facts=key_facts,
        key_aspects=key_aspects,
        socionics=socionics,
        archetype=archetype,
        strengths=grouped_claims["strengths"],
        risks=grouped_claims["risks"],
        relationship_patterns=grouped_claims["relationship_patterns"],
        sexuality_patterns=grouped_claims["sexuality_patterns"],
        development_recommendations=grouped_claims["development_recommendations"],
        product_boundaries=ProductBoundaries(
            career_policy=(
                "В Self-отчёте карьеру затрагивать кратко и завершать CTA на Career. "
                "Не давать список профессий, деньги, стратегию роста и управленческий разбор."
            ),
            allowed_sections=SELF_ALLOWED_SECTIONS,
        ),
    )


def _parse_birth_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    return date(1970, 1, 1)


def _quality_label(birth_time_quality: str) -> str:
    if birth_time_quality == "exact":
        return "Высокая точность времени рождения"
    if birth_time_quality == "approximate":
        return "Приблизительное время рождения"
    return "Время рождения неизвестно"


def _planet_fact(planet: dict[str, Any]) -> AstroFact:
    planet_name = PLANET_RU.get(str(planet.get("name")), str(planet.get("name")))
    sign_name = SIGN_RU.get(str(planet.get("sign")), str(planet.get("sign")))
    house = planet.get("house")
    fact_id = f"{str(planet.get('name', '')).lower()}_{str(planet.get('sign', '')).lower()}_house_{house}"
    label = f"{planet_name} в {sign_name} в {house} доме" if house is not None else f"{planet_name} в {sign_name}"
    meaning = f"Положение {planet_name.lower()} помогает описать устойчивый личный паттерн в рамках Self-отчёта."
    return AstroFact(id=fact_id, label=label, meaning=meaning)


def _aspect_fact(aspect: dict[str, Any]) -> AspectFact:
    left = PLANET_RU.get(str(aspect.get("planet_a")), str(aspect.get("planet_a")))
    right = PLANET_RU.get(str(aspect.get("planet_b")), str(aspect.get("planet_b")))
    aspect_name = ASPECT_RU.get(str(aspect.get("aspect_type")), str(aspect.get("aspect_type")))
    fact_id = (
        f"{str(aspect.get('planet_a', '')).lower()}_"
        f"{str(aspect.get('aspect_type', '')).lower()}_"
        f"{str(aspect.get('planet_b', '')).lower()}"
    )
    orb_value = aspect.get("orb", 0)
    orb = f"{orb_value:.2f}°" if isinstance(orb_value, int | float) else str(orb_value)
    meaning = f"Аспект {left.lower()} и {right.lower()} показывает связь между двумя психологическими акцентами."
    return AspectFact(id=fact_id, label=f"{left} {aspect_name} {right}", orb=orb, meaning=meaning)


def _group_claims(claims: list[dict[str, Any]]) -> dict[str, list[EvidenceBackedClaim]]:
    grouped: dict[str, list[EvidenceBackedClaim]] = {
        "strengths": [],
        "risks": [],
        "relationship_patterns": [],
        "sexuality_patterns": [],
        "development_recommendations": [],
    }
    for claim in claims:
        target = SECTION_MAP.get(str(claim.get("section")))
        if target is None:
            continue
        grouped[target].append(
            EvidenceBackedClaim(
                id=str(claim.get("claim_id", "claim")),
                claim=str(claim.get("message", "")),
                evidence_ids=_extract_evidence_ids(claim),
            )
        )

    for key in grouped:
        grouped[key].sort(key=lambda item: item.id)
    return grouped


def _extract_evidence_ids(claim: dict[str, Any]) -> list[str]:
    evidence_ids: list[str] = []
    for item in claim.get("basis", []):
        rule_id = item.get("rule_id")
        if isinstance(rule_id, str) and rule_id not in evidence_ids:
            evidence_ids.append(rule_id)
    return evidence_ids or [str(claim.get("claim_id", "claim"))]
