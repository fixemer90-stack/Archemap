# ruff: noqa: RUF001, E501
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
    HouseScenario,
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

HOUSE_SCENARIO_TEMPLATES: dict[int, dict[str, str]] = {
    1: {
        "need": "Почувствовать право быть видимым и действовать от первого лица.",
        "manifestation": "Жизненный сценарий часто начинается с темы самопрезентации, первого импульса и личной инициативы.",
        "shadow": "Можно слишком быстро отождествляться с первым впечатлением и реагировать раньше, чем ситуация понята.",
        "mature_expression": "Зрелая форма — выбирать ясную позицию и проявляться без необходимости всё время доказывать своё право на место.",
    },
    2: {
        "need": "Иметь устойчивую опору: ценности, ресурсы, телесный ритм и чувство собственной достаточности.",
        "manifestation": "Паттерн проявляется через отношение к стабильности, накоплению сил и тому, что действительно ценно.",
        "shadow": "Можно застревать в контроле безопасности или измерять себя только через полезность и ресурс.",
        "mature_expression": "Зрелая форма — строить устойчивость без внутреннего сжатия и признавать ценность до внешнего подтверждения.",
    },
    3: {
        "need": "Понимать происходящее через обмен, обучение, наблюдение и точную формулировку.",
        "manifestation": "Жизненный сценарий разворачивается через разговоры, короткие связи, обучение и сбор живой информации.",
        "shadow": "Можно дробить внимание, объяснять вместо чувствовать или оставаться в бесконечном анализе деталей.",
        "mature_expression": "Зрелая форма — превращать поток впечатлений в ясный язык и своевременное действие.",
    },
    4: {
        "need": "Иметь внутренний дом: эмоциональную базу, память, корни и безопасное место возвращения.",
        "manifestation": "Сильные переживания часто связываются с семьёй, приватностью, близким кругом и ощущением принадлежности.",
        "shadow": "Можно уходить в защиту, прошлое или зависимость от привычной эмоциональной среды.",
        "mature_expression": "Зрелая форма — создавать устойчивую внутреннюю опору, не замыкаясь в старом сценарии.",
    },
    5: {
        "need": "Выражать себя творчески, играть, любить и оставлять личный след.",
        "manifestation": "Сценарий заметен в желании быть живым автором происходящего, а не только исполнителем чужой формы.",
        "shadow": "Можно зависеть от реакции аудитории или драматизировать там, где нужна простая честность.",
        "mature_expression": "Зрелая форма — создавать и любить без постоянной проверки собственной яркости.",
    },
    6: {
        "need": "Собрать жизнь в рабочий порядок: режим, навык, заботу о теле и полезность действий.",
        "manifestation": "Паттерн проявляется через качество ежедневных процессов, внимание к деталям и способность улучшать систему.",
        "shadow": "Можно перегружаться исправлением несовершенств и превращать заботу в контроль.",
        "mature_expression": "Зрелая форма — поддерживать порядок как ресурс, а не как бесконечный экзамен на правильность.",
    },
    7: {
        "need": "Видеть себя через встречу с другим: партнёрство, диалог, выбор дистанции и договорённость.",
        "manifestation": "Ключевые ситуации часто запускаются через отношения, союзников, оппонентов и необходимость учитывать вторую сторону.",
        "shadow": "Можно слишком подстраиваться под отражение другого или ожидать, что контакт сам задаст личную позицию.",
        "mature_expression": "Зрелая форма — быть в близком диалоге, не теряя собственного центра.",
    },
    8: {
        "need": "Понимать глубину переживаний, доверие, кризисы, границы и обмен силой.",
        "manifestation": "Жизненный сценарий часто связан с интенсивностью, тайными мотивами, близостью и способностью проходить трансформации.",
        "shadow": "Можно застревать в подозрительности, эмоциональном контроле или драматизации риска.",
        "mature_expression": "Зрелая форма — выдерживать интенсивность без разрушения доверия и превращать кризис в ясность.",
    },
    9: {
        "need": "Иметь собственную систему мировоззрения, а не просто набор фактов.",
        "manifestation": "Вы ищете методологии, объяснения, образование и язык, который собирает картину мира.",
        "shadow": "Можно застревать в поиске правильной системы и откладывать действие.",
        "mature_expression": "Зрелая форма — превращать знание в понятную позицию и практический выбор.",
    },
    10: {
        "need": "Видеть направление, ответственность, социальную роль и форму результата.",
        "manifestation": "Паттерн проявляется через отношение к признанию, ответственности, статусу и долгосрочной траектории.",
        "shadow": "Можно превращать жизнь в проект достижений или слишком зависеть от внешней оценки результата.",
        "mature_expression": "Зрелая форма — строить заметный результат без потери человеческого масштаба и внутренней честности.",
    },
    11: {
        "need": "Найти своё место среди людей, идей, сообществ и будущих возможностей.",
        "manifestation": "Сценарий разворачивается через друзей, группы, проекты, сети и чувство общей перспективы.",
        "shadow": "Можно растворяться в группе, жить ожиданием будущего или путать мечту с конкретным шагом.",
        "mature_expression": "Зрелая форма — соединять личную уникальность с вкладом в общую систему.",
    },
    12: {
        "need": "Слышать скрытый внутренний слой: тишину, бессознательные мотивы, одиночество и тонкую эмпатию.",
        "manifestation": "Паттерн часто проявляется через глубокую чувствительность, приватные переживания и потребность периодически уходить внутрь.",
        "shadow": "Можно исчезать из прямого действия, копить невыраженное напряжение или спасать других ценой себя.",
        "mature_expression": "Зрелая форма — сохранять тонкость восприятия и при этом оставаться в ясных границах реальной жизни.",
    },
}

SCENARIO_PLANET_PRIORITY = {
    "Sun": 0,
    "Moon": 1,
    "Mercury": 2,
    "Venus": 3,
    "Mars": 4,
    "Jupiter": 5,
    "Saturn": 6,
    "Uranus": 7,
    "Neptune": 8,
    "Pluto": 9,
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
    house_scenarios = _build_house_scenarios(chart, key_facts)

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
        house_scenarios=house_scenarios,
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


def _build_house_scenarios(chart: dict[str, Any], key_facts: list[AstroFact]) -> list[HouseScenario]:
    planets = [planet for planet in chart.get("planets", []) if planet.get("name") and planet.get("sign")]
    fact_ids_by_planet = _fact_ids_by_planet(key_facts)
    scenario_planets = sorted(
        planets,
        key=lambda planet: (
            SCENARIO_PLANET_PRIORITY.get(str(planet.get("name")), 99),
            int(planet.get("house", 99)) if isinstance(planet.get("house"), int) else 99,
        ),
    )
    scenarios: list[HouseScenario] = []
    seen: set[str] = set()
    for planet in scenario_planets:
        scenario = _house_scenario_for_planet(planet, fact_ids_by_planet)
        if scenario is None or scenario.id in seen:
            continue
        seen.add(scenario.id)
        scenarios.append(scenario)
        if len(scenarios) >= 5:
            break
    return scenarios


def _house_scenario_for_planet(
    planet: dict[str, Any],
    fact_ids_by_planet: dict[str, str],
) -> HouseScenario | None:
    planet_name_raw = str(planet.get("name"))
    sign_raw = str(planet.get("sign"))
    house = planet.get("house")
    if not isinstance(house, int) or house not in HOUSE_SCENARIO_TEMPLATES:
        return None
    fact_id = fact_ids_by_planet.get(planet_name_raw)
    if not fact_id:
        return None
    planet_name = PLANET_RU.get(planet_name_raw, planet_name_raw)
    sign_name = SIGN_RU.get(sign_raw, sign_raw)
    template = HOUSE_SCENARIO_TEMPLATES[house]
    return HouseScenario(
        id=f"house_scenario_{planet_name_raw.lower()}_{house}",
        title=f"{planet_name} в {house} доме",
        placement=f"{planet_name} в {sign_name} в {house} доме",
        need=template["need"],
        manifestation=_planet_contextualize(planet_name, template["manifestation"]),
        shadow=template["shadow"],
        mature_expression=template["mature_expression"],
        evidence_ids=[fact_id],
    )


def _planet_contextualize(planet_name: str, manifestation: str) -> str:
    planet_context = {
        "Солнце": "Для Солнца это становится способом строить личный авторитет и чувство направления. ",
        "Луна": "Для Луны это окрашивает эмоциональную безопасность, привычные реакции и способ восстановления. ",
        "Меркурий": "Для Меркурия это проявляется в мышлении, речи, обучении и выборе языка описания. ",
        "Венера": "Для Венеры это влияет на вкус, близость, симпатию и способ выбирать ценное. ",
        "Марс": "Для Марса это задаёт стиль действия, напора, защиты границ и прямой реакции. ",
    }
    return f"{planet_context.get(planet_name, '')}{manifestation}"


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
