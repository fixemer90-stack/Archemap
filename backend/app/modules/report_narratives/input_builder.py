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
    DominantInsight,
    EvidenceBackedClaim,
    InnerMechanism,
    MechanismStep,
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

SIGN_RU_NOMINATIVE = {
    "Aries": "Овен",
    "Taurus": "Телец",
    "Gemini": "Близнецы",
    "Cancer": "Рак",
    "Leo": "Лев",
    "Virgo": "Дева",
    "Libra": "Весы",
    "Scorpio": "Скорпион",
    "Sagittarius": "Стрелец",
    "Capricorn": "Козерог",
    "Aquarius": "Водолей",
    "Pisces": "Рыбы",
}

ELEMENT_RU = {
    "fire": "Огонь",
    "earth": "Земля",
    "air": "Воздух",
    "water": "Вода",
}

MODALITY_RU = {
    "cardinal": "кардинальность",
    "fixed": "фиксированность",
    "mutable": "мутабельность",
}

SIGN_ELEMENT = {
    "Aries": "fire",
    "Leo": "fire",
    "Sagittarius": "fire",
    "Taurus": "earth",
    "Virgo": "earth",
    "Capricorn": "earth",
    "Gemini": "air",
    "Libra": "air",
    "Aquarius": "air",
    "Cancer": "water",
    "Scorpio": "water",
    "Pisces": "water",
}

SIGN_MODALITY = {
    "Aries": "cardinal",
    "Cancer": "cardinal",
    "Libra": "cardinal",
    "Capricorn": "cardinal",
    "Taurus": "fixed",
    "Leo": "fixed",
    "Scorpio": "fixed",
    "Aquarius": "fixed",
    "Gemini": "mutable",
    "Virgo": "mutable",
    "Sagittarius": "mutable",
    "Pisces": "mutable",
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
    dominants = _build_dominants(chart, key_facts, key_aspects)
    if not dominants:
        dominants = _fallback_dominants_from_claims(grouped_claims)
    inner_mechanism = _build_inner_mechanism(dominants)

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
        dominants=dominants,
        inner_mechanism=inner_mechanism,
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


def _build_dominants(
    chart: dict[str, Any],
    key_facts: list[AstroFact],
    key_aspects: list[AspectFact],
) -> list[DominantInsight]:
    planets = [planet for planet in chart.get("planets", []) if planet.get("name") and planet.get("sign")]
    fact_ids_by_planet = _fact_ids_by_planet(key_facts)
    dominants: list[DominantInsight] = []

    element = _top_weighted_key(chart.get("elements", {}), ELEMENT_RU)
    if element is not None:
        evidence_ids = _evidence_for_sign_attribute(planets, fact_ids_by_planet, SIGN_ELEMENT, element)
        if evidence_ids:
            dominants.append(
                DominantInsight(
                    id=f"dominant_element_{element}",
                    title=f"Доминирующая стихия: {ELEMENT_RU[element]}",
                    body=(
                        f"{ELEMENT_RU[element]} задаёт базовый способ адаптации: через повторяющийся "
                        "паттерн восприятия, реакции и выбора опоры."
                    ),
                    evidence_ids=evidence_ids,
                )
            )

    modality = _top_weighted_key(chart.get("modalities", {}), MODALITY_RU)
    if modality is not None:
        evidence_ids = _evidence_for_sign_attribute(planets, fact_ids_by_planet, SIGN_MODALITY, modality)
        if evidence_ids:
            dominants.append(
                DominantInsight(
                    id=f"dominant_modality_{modality}",
                    title=f"Ведущая модальность: {MODALITY_RU[modality]}",
                    body=(
                        f"{MODALITY_RU[modality].capitalize()} показывает, как энергия карты переходит "
                        "от внутреннего импульса к действию и устойчивому поведению."
                    ),
                    evidence_ids=evidence_ids,
                )
            )

    house, house_evidence = _top_house_cluster(planets, fact_ids_by_planet)
    if house is not None and house_evidence:
        dominants.append(
            DominantInsight(
                id=f"dominant_house_{house}",
                title=f"Сильный акцент {house} дома",
                body=(
                    f"Повторяющиеся положения в {house} доме показывают жизненную сцену, "
                    "где личный паттерн проявляется особенно заметно."
                ),
                evidence_ids=house_evidence,
            )
        )

    sign, sign_evidence = _top_sign_cluster(planets, fact_ids_by_planet)
    if sign is not None and sign_evidence:
        sign_label = SIGN_RU_NOMINATIVE.get(sign, sign)
        dominants.append(
            DominantInsight(
                id=f"dominant_sign_{sign.lower()}",
                title=f"Повторяющийся знак: {sign_label}",
                body=(
                    f"Акцент знака {sign_label} повторяет один и тот же психологический мотив "
                    "в нескольких частях карты."
                ),
                evidence_ids=sign_evidence,
            )
        )

    tension = _first_tension_aspect(key_aspects)
    if tension is not None:
        dominants.append(
            DominantInsight(
                id=f"dominant_tension_{tension.id}",
                title="Ключевое напряжение карты",
                body=(
                    f"{tension.label} добавляет внутренний контраст: не только сильную сторону, "
                    "но и сценарий напряжения, который важно осознанно регулировать."
                ),
                evidence_ids=[tension.id],
            )
        )

    if not dominants and key_facts:
        first_fact = key_facts[0]
        dominants.append(
            DominantInsight(
                id="dominant_primary_fact",
                title="Главный доступный акцент карты",
                body=f"{first_fact.label} — первый устойчивый факт, на который можно опереться в Self-разборе.",
                evidence_ids=[first_fact.id],
            )
        )
    if not dominants and key_aspects:
        first_aspect = key_aspects[0]
        dominants.append(
            DominantInsight(
                id="dominant_primary_aspect",
                title="Главная доступная связка карты",
                body=f"{first_aspect.label} — первый устойчивый аспект, на который можно опереться в Self-разборе.",
                evidence_ids=[first_aspect.id],
            )
        )

    return dominants[:5]


def _fallback_dominants_from_claims(grouped_claims: dict[str, list[EvidenceBackedClaim]]) -> list[DominantInsight]:
    for group in grouped_claims.values():
        if not group:
            continue
        claim = group[0]
        if claim.evidence_ids:
            return [
                DominantInsight(
                    id="dominant_primary_claim",
                    title="Главный доступный смысловой акцент",
                    body=claim.claim,
                    evidence_ids=list(claim.evidence_ids),
                )
            ]
    return []


def _build_inner_mechanism(dominants: list[DominantInsight]) -> InnerMechanism:
    source = dominants or [
        DominantInsight(
            id="dominant_fallback",
            title="Базовый акцент карты",
            body="Доступные факты карты задают осторожный базовый Self-паттерн.",
            evidence_ids=["dominant_fallback"],
        )
    ]
    first = source[0]
    second = source[1] if len(source) > 1 else source[0]
    third = source[2] if len(source) > 2 else source[-1]
    return InnerMechanism(
        title="Внутренний механизм личности",
        summary=(
            "Эти доминанты описывают не набор отдельных качеств, а последовательность: "
            "как вы считываете ситуацию, собираете опору и переводите внутренний импульс в действие."
        ),
        steps=[
            MechanismStep(
                id="mechanism_read_context",
                title="Сначала вы считываете, что в ситуации главное",
                body=f"На первом шаге включается «{first.title}»: он задаёт первичный фильтр восприятия.",
                evidence_ids=list(first.evidence_ids),
            ),
            MechanismStep(
                id="mechanism_build_support",
                title="Затем ищете рабочую внутреннюю опору",
                body=f"После первичного считывания «{second.title}» помогает собрать устойчивую форму реакции.",
                evidence_ids=list(second.evidence_ids),
            ),
            MechanismStep(
                id="mechanism_express_pattern",
                title="После этого проявляете паттерн вовне",
                body=(
                    f"Внешнее действие окрашивается темой «{third.title}»: так внутренний вывод становится поведением."
                ),
                evidence_ids=list(third.evidence_ids),
            ),
        ],
    )


def _top_weighted_key(values: Any, labels: dict[str, str]) -> str | None:
    if not isinstance(values, dict):
        return None
    numeric_values = {
        str(key): float(value)
        for key, value in values.items()
        if key in labels and isinstance(value, int | float) and float(value) > 0
    }
    if not numeric_values:
        return None
    return max(numeric_values.items(), key=lambda item: item[1])[0]


def _fact_ids_by_planet(key_facts: list[AstroFact]) -> dict[str, str]:
    result: dict[str, str] = {}
    for fact in key_facts:
        planet = fact.id.split("_", 1)[0]
        if planet:
            result[planet.title()] = fact.id
    return result


def _evidence_for_sign_attribute(
    planets: list[dict[str, Any]],
    fact_ids_by_planet: dict[str, str],
    sign_map: dict[str, str],
    target: str,
) -> list[str]:
    evidence_ids: list[str] = []
    for planet in planets:
        if sign_map.get(str(planet.get("sign"))) != target:
            continue
        fact_id = fact_ids_by_planet.get(str(planet.get("name")))
        if fact_id and fact_id not in evidence_ids:
            evidence_ids.append(fact_id)
    return evidence_ids


def _top_house_cluster(
    planets: list[dict[str, Any]],
    fact_ids_by_planet: dict[str, str],
) -> tuple[int | None, list[str]]:
    house_counts: dict[int, list[str]] = {}
    for planet in planets:
        house = planet.get("house")
        if not isinstance(house, int):
            continue
        fact_id = fact_ids_by_planet.get(str(planet.get("name")))
        if fact_id:
            house_counts.setdefault(house, []).append(fact_id)
    if not house_counts:
        return None, []
    house = max(house_counts, key=lambda item: (len(house_counts[item]), -item))
    return house, house_counts[house]


def _top_sign_cluster(
    planets: list[dict[str, Any]],
    fact_ids_by_planet: dict[str, str],
) -> tuple[str | None, list[str]]:
    sign_counts: dict[str, list[str]] = {}
    for planet in planets:
        sign = planet.get("sign")
        if not isinstance(sign, str):
            continue
        fact_id = fact_ids_by_planet.get(str(planet.get("name")))
        if fact_id:
            sign_counts.setdefault(sign, []).append(fact_id)
    if not sign_counts:
        return None, []
    sign = max(sign_counts, key=lambda item: (len(sign_counts[item]), item))
    return sign, sign_counts[sign]


def _first_tension_aspect(key_aspects: list[AspectFact]) -> AspectFact | None:
    for aspect in key_aspects:
        label = aspect.label.lower()
        if "квадрат" in label or "оппозиция" in label:
            return aspect
    return None


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
