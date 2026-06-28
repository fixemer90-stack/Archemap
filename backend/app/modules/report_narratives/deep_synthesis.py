# ruff: noqa: RUF001
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
    chart_dynamics = [
        ChartDynamic(
            id=f"chart_dynamic_{dominant.id}",
            title=dominant.title,
            mechanism=dominant.body,
            tension="Эта динамика создаёт внутреннее напряжение между импульсом и способом его выражения.",
            compensation="Компенсация приходит через осознанную настройку ритма и выбора формы контакта.",
            section_targets=["main_formula", "development"],
            evidence_ids=list(dominant.evidence_ids),
        )
        for dominant in narrative_input.dominants[:3]
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
    calibration_hypotheses = [
        CalibrationHypothesis(
            id=f"calibration_{question.id}",
            hypothesis=question.question,
            answer_type=question.answer_type,
            evidence_ids=list(question.evidence_ids),
        )
        for question in narrative_input.calibration_questions
    ]
    maturity_levels = MaturityLevels(
        low=MaturityBand(
            title=narrative_input.maturity_levels.low.title,
            body=narrative_input.maturity_levels.low.body,
            evidence_ids=list(narrative_input.maturity_levels.low.evidence_ids),
        ),
        medium=MaturityBand(
            title=narrative_input.maturity_levels.medium.title,
            body=narrative_input.maturity_levels.medium.body,
            evidence_ids=list(narrative_input.maturity_levels.medium.evidence_ids),
        ),
        high=MaturityBand(
            title=narrative_input.maturity_levels.high.title,
            body=narrative_input.maturity_levels.high.body,
            evidence_ids=list(narrative_input.maturity_levels.high.evidence_ids),
        ),
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
        contradictions=narrative_input.contradictions,
        maturity_levels=maturity_levels,
        calibration_hypotheses=calibration_hypotheses,
    )
