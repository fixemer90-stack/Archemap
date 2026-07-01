# ruff: noqa: RUF001, E501
"""Deterministic DeepNatalSynthesis builder for staged narrative pipeline."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.modules.report_narratives.aspect_synthesis import (
    cluster_aspect_patterns,
    rank_chart_aspects,
)
from app.modules.report_narratives.schemas import (
    AspectFact,
    AspectPattern,
    AstroFact,
    CalibrationHypothesis,
    ChartDynamic,
    DeepNatalSynthesis,
    HouseAxisPattern,
    MaturityBand,
    MaturityLevels,
    PlanetRole,
    RankedAspect,
)

DEEP_NATAL_SYNTHESIS_CONTRACT_VERSION = "deep_natal_synthesis_v1"


def _chart_evidence_ids(
    *groups: list[str],
) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for group in groups:
        for item in group:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
    return ordered


def _canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        canonical_items = [_canonicalize(item) for item in value]
        return sorted(canonical_items, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True))
    return value


def compute_deep_synthesis_hash(synthesis: DeepNatalSynthesis) -> str:
    payload = synthesis.model_dump(mode="json")
    normalized = _canonicalize(payload)
    serialized = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _build_chart_dynamics(
    aspect_patterns: list[AspectPattern],
    house_axis_patterns: list[HouseAxisPattern],
    planet_roles: list[PlanetRole],
) -> list[ChartDynamic]:
    dynamics: list[ChartDynamic] = []
    by_id = {pattern.id: pattern for pattern in aspect_patterns}
    house_by_id = {pattern.id: pattern for pattern in house_axis_patterns}

    moon_saturn = by_id.get("saturn_boundary_pattern")
    if moon_saturn and any("moon_opposition_saturn" in item for item in moon_saturn.aspect_ids):
        dynamics.append(
            ChartDynamic(
                id="chart_dynamic_moon_saturn_regulation",
                title="Напряжение между чувственным импульсом и внутренним контролем",
                mechanism="Реакция возникает быстро, но почти сразу встречает внутреннюю проверку на уместность, силу и последствия.",
                tension="Из-за этого человек одновременно хочет выразиться и тут же сдерживает себя, чтобы не потерять управление ситуацией.",
                compensation="Компенсация приходит, когда эмоция сначала получает форму и язык, а уже потом проходит внутреннюю цензуру.",
                section_targets=["emotions_and_communication", "development"],
                evidence_ids=_chart_evidence_ids(moon_saturn.aspect_ids),
            )
        )

    venus_mars = by_id.get("venus_mars_pattern")
    if venus_mars:
        dynamics.append(
            ChartDynamic(
                id="chart_dynamic_venus_mars_intimacy",
                title="Близость как поле притяжения и самозащиты",
                mechanism="Тяга к взаимности включается вместе с высокой чувствительностью к дисбалансу, реакции другого и угрозе внутренней уязвимости.",
                tension="Поэтому контакт может одновременно манить и вызывать защитную реакцию, если нет ощущения равновесия и безопасности.",
                compensation="Компенсация появляется, когда желание обсуждается прямо, а не уходит в обиду, проверку или пассивное сопротивление.",
                section_targets=["relationships", "sexuality"],
                evidence_ids=_chart_evidence_ids(venus_mars.aspect_ids),
            )
        )

    depth_axis = house_by_id.get("house_axis_house_scenario_sun_9")
    moon_depth = house_by_id.get("house_axis_house_scenario_moon_8")
    if depth_axis or moon_depth:
        evidence_ids = _chart_evidence_ids(
            depth_axis.evidence_ids if depth_axis else [],
            moon_depth.evidence_ids if moon_depth else [],
        )
        dynamics.append(
            ChartDynamic(
                id="chart_dynamic_identity_depth_axis",
                title="Направление между смыслом, глубиной и личной позицией",
                mechanism="Человеку мало просто реагировать на происходящее: ему нужно собрать из переживания цельную систему смысла и внутреннюю позицию.",
                tension="Из-за этого он может застревать между потребностью понять всё глубоко и необходимостью всё же выбрать ясный вектор действия.",
                compensation="Компенсация возникает, когда глубина переживания превращается не в круговое самокопание, а в сформулированный выбор и язык позиции.",
                section_targets=["main_formula", "world_perception"],
                evidence_ids=evidence_ids,
            )
        )

    return dynamics[:5]


def _build_contradictions(
    chart_dynamics: list[ChartDynamic],
    aspect_patterns: list[AspectPattern],
    house_axis_patterns: list[HouseAxisPattern],
) -> list[Any]:
    from app.modules.report_narratives.schemas import ContradictionInsight

    contradictions: list[ContradictionInsight] = []
    dynamic_by_id = {item.id: item for item in chart_dynamics}

    if "chart_dynamic_moon_saturn_regulation" in dynamic_by_id:
        contradictions.append(
            ContradictionInsight(
                id="contradiction_moon_saturn_expression_vs_control",
                title="Выразить чувство или удержать контроль",
                tension="Эмоциональная правда хочет проявиться сразу, но внутренняя часть, отвечающая за контроль и последствия, быстро включает торможение.",
                manifestation="Снаружи это может выглядеть как чередование сильной включённости и резкой собранности, когда человек уже почувствовал многое, но показывает только безопасный фрагмент.",
                mature_expression="Зрелая форма — не подавлять чувство, а давать ему форму: сначала назвать, что происходит, и только потом решать, как именно это выражать.",
                evidence_ids=_chart_evidence_ids(dynamic_by_id["chart_dynamic_moon_saturn_regulation"].evidence_ids),
            )
        )

    if "chart_dynamic_venus_mars_intimacy" in dynamic_by_id:
        contradictions.append(
            ContradictionInsight(
                id="contradiction_venus_mars_closeness_vs_defense",
                title="Тянуться к близости и одновременно защищаться от неё",
                tension="Потребность в контакте сочетается с быстрой реакцией на дисбаланс, давление или неоднозначность со стороны другого.",
                manifestation="Поэтому в отношениях может появляться смесь притяжения, проверки, обиды или защитной дистанции, хотя сама потребность в близости остаётся сильной.",
                mature_expression="Зрелая форма — переводить напряжение в прямой разговор о желании, темпе и границах, не превращая уязвимость в скрытую борьбу.",
                evidence_ids=_chart_evidence_ids(dynamic_by_id["chart_dynamic_venus_mars_intimacy"].evidence_ids),
            )
        )

    if "chart_dynamic_identity_depth_axis" in dynamic_by_id:
        contradictions.append(
            ContradictionInsight(
                id="contradiction_depth_vs_direction",
                title="Понять глубже или уже выбрать направление",
                tension="Внутренняя работа над смыслом и глубиной переживания может затягиваться, если решение кажется слишком поверхностным или преждевременным.",
                manifestation="Это проявляется как склонность ещё дорабатывать картину мира, когда снаружи уже нужен язык позиции, шаг или объявленный вектор.",
                mature_expression="Зрелая форма — разрешить себе промежуточную ясность: выбирать достаточно точную позицию без требования сначала понять вообще всё.",
                evidence_ids=_chart_evidence_ids(dynamic_by_id["chart_dynamic_identity_depth_axis"].evidence_ids),
            )
        )

    for pattern in aspect_patterns:
        if len(contradictions) >= 5:
            break
        if pattern.id in {"moon_mercury_pattern", "venus_mars_pattern", "saturn_boundary_pattern"}:
            continue
        contradictions.append(
            ContradictionInsight(
                id=f"contradiction_{pattern.id}",
                title=f"Напряжение внутри паттерна «{pattern.title.lower()}»",
                tension=pattern.psychological_mechanism,
                manifestation=pattern.life_manifestation,
                mature_expression=pattern.mature_expression,
                evidence_ids=_chart_evidence_ids(pattern.aspect_ids or pattern.evidence_ids),
            )
        )

    return contradictions[:5]


def _build_calibration_hypotheses(
    chart_dynamics: list[ChartDynamic],
    contradictions: list[Any],
) -> list[CalibrationHypothesis]:
    hypotheses: list[CalibrationHypothesis] = []
    for item in chart_dynamics:
        hypotheses.append(
            CalibrationHypothesis(
                id=f"calibration_{item.id}",
                hypothesis=f"Когда напряжение по теме «{item.title.lower()}» растёт, замечаете ли вы, что сначала сдерживаете реакцию, а уже потом ищете язык для неё?",
                answer_type="scale_1_5",
                evidence_ids=list(item.evidence_ids),
            )
        )
    for contradiction in contradictions:
        if len(hypotheses) >= 7:
            break
        hypotheses.append(
            CalibrationHypothesis(
                id=f"calibration_{contradiction.id}",
                hypothesis=f"Когда проявляется тема «{contradiction.title.lower()}», замечаете ли вы повторяемый сценарий именно в живом контакте, а не только в мыслях?",
                answer_type="yes_no",
                evidence_ids=list(contradiction.evidence_ids),
            )
        )
    return hypotheses[:7]


def _build_maturity_levels(
    contradictions: list[Any],
    chart_dynamics: list[ChartDynamic],
    fallback_evidence_ids: list[str],
) -> MaturityLevels:
    evidence_ids = _chart_evidence_ids(
        *[item.evidence_ids for item in contradictions[:3]],
        *[item.evidence_ids for item in chart_dynamics[:2]],
    )
    if not evidence_ids:
        evidence_ids = list(fallback_evidence_ids)
    return MaturityLevels(
        low=MaturityBand(
            title="Паттерн живёт как автоматическая защита",
            body="На низком уровне напряжение проживается реактивно: человек либо сдерживает важное до перегруза, либо действует из внутреннего давления, не успев собрать переживание в ясную форму.",
            evidence_ids=evidence_ids,
        ),
        medium=MaturityBand(
            title="Осознавание уже есть, но устойчивости не хватает",
            body="На среднем уровне человек уже замечает свои повторяющиеся механизмы, но всё ещё легко срывается в старую схему, если контакт, ответственность или близость становятся слишком значимыми.",
            evidence_ids=evidence_ids,
        ),
        high=MaturityBand(
            title="Напряжение превращается в управляемую глубину",
            body="На высоком уровне те же противоречия становятся источником точности: чувство не подавляется, границы не каменеют, а глубина переживания переводится в выбранную позицию, ритм и форму контакта.",
            evidence_ids=evidence_ids,
        ),
    )


def build_deep_natal_synthesis(report: Any) -> DeepNatalSynthesis:
    from app.modules.report_narratives.input_builder import build_narrative_input

    narrative_input = build_narrative_input(report, include_deep_synthesis=False)
    evidence_items: list[AstroFact | AspectFact] = [*narrative_input.key_facts, *narrative_input.key_aspects]
    evidence_map: dict[str, AstroFact | AspectFact] = {fact.id: fact for fact in evidence_items}
    fallback_ids = list(evidence_map)[:2] or ["chart_summary"]
    source_chart_snapshot_id = ((report.report_data or {}).get("source_chart") or {}).get(
        "snapshot_id"
    ) or "chart:unknown"

    ranked_aspects = rank_chart_aspects((report.report_data or {}).get("chart", {}))
    if not ranked_aspects and fallback_ids:
        ranked_aspects = [
            RankedAspect(
                id="ranked_chart_fallback",
                label="Базовая динамика карты",
                weight=0.1,
                evidence_ids=fallback_ids,
                section_targets=["main_formula"],
            )
        ]

    aspect_patterns = cluster_aspect_patterns((report.report_data or {}).get("chart", {}), ranked_aspects)
    if not aspect_patterns and fallback_ids:
        aspect_patterns = [
            AspectPattern(
                id="aspect_pattern_fallback",
                title="Базовый паттерн карты",
                aspect_ids=[],
                planets=[],
                pattern_type="mixed",
                psychological_mechanism=(
                    "Даже без выраженных аспектов карта собирается вокруг повторяющегося способа "
                    "воспринимать и структурировать опыт."
                ),
                life_manifestation="Это проявляется в повторяемой манере реагировать на нагрузку и выбирать опору.",
                risk="Без осознавания паттерн может казаться просто привычным фоном.",
                mature_expression="При осознавании он становится точкой сборки, а не автоматизмом.",
                section_targets=["main_formula"],
                evidence_ids=fallback_ids,
                weight=0.1,
            )
        ]

    planet_roles = [
        PlanetRole(
            id=f"planet_role_{fact.id}",
            title=fact.label,
            function=fact.meaning,
            influence="Эта роль влияет на то, как человек воспринимает требования ситуации и выбирает форму ответа.",
            section_targets=["main_formula", "strengths"],
            evidence_ids=[fact.id],
        )
        for fact in narrative_input.key_facts[:3]
    ]
    house_axis_patterns = [
        HouseAxisPattern(
            id=f"house_axis_{scenario.id}",
            title=scenario.title,
            axis=f"Дом {scenario.placement}",
            mechanism=scenario.need,
            manifestation=scenario.manifestation,
            evidence_ids=list(scenario.evidence_ids),
            section_targets=["relationships", "development"],
        )
        for scenario in narrative_input.house_scenarios[:2]
    ]
    chart_dynamics = _build_chart_dynamics(
        aspect_patterns=aspect_patterns,
        house_axis_patterns=house_axis_patterns,
        planet_roles=planet_roles,
    )
    contradictions = _build_contradictions(
        chart_dynamics=chart_dynamics,
        aspect_patterns=aspect_patterns,
        house_axis_patterns=house_axis_patterns,
    )
    calibration_hypotheses = _build_calibration_hypotheses(
        chart_dynamics=chart_dynamics,
        contradictions=contradictions,
    )
    maturity_levels = _build_maturity_levels(
        contradictions=contradictions,
        chart_dynamics=chart_dynamics,
        fallback_evidence_ids=fallback_ids,
    )

    return DeepNatalSynthesis(
        contract_version=DEEP_NATAL_SYNTHESIS_CONTRACT_VERSION,
        source_chart_snapshot_id=source_chart_snapshot_id,
        evidence_map=evidence_map,
        ranked_aspects=ranked_aspects,
        aspect_patterns=aspect_patterns,
        house_axis_patterns=house_axis_patterns,
        planet_roles=planet_roles,
        chart_dynamics=chart_dynamics,
        contradictions=contradictions,
        maturity_levels=maturity_levels,
        calibration_hypotheses=calibration_hypotheses,
    )
