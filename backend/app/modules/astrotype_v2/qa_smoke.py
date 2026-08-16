"""Deterministic QA/smoke bundle builders for Astrotype v2 rollout gates."""

# ruff: noqa: RUF001

from __future__ import annotations

import json
import uuid
from collections.abc import Iterable
from typing import Any

from app.modules.astrotype_v2 import models
from app.modules.astrotype_v2.api_runtime import build_report_progress_v2, build_report_read_payload_v2
from app.modules.astrotype_v2.infographic_data import build_natal_infographic_data_row
from app.modules.astrotype_v2.outline import build_report_outline_row
from app.modules.astrotype_v2.report_assembler import build_natal_report_row
from app.modules.astrotype_v2.schemas import ReportSegmentOutputV2
from app.modules.astrotype_v2.synthesis import build_natal_synthesis_row

_SMOKE_SOURCE_VERSION = "v2.0"
_FORBIDDEN_TYPOLOGY_TOKENS = (
    "socionics",
    "model a",
    "function strength",
    "function-strength",
    "archetype",
    "типология",
    "соционик",
)

_SECTION_COPY = {
    "core_pattern": (
        "Ядро личности",
        "Эта секция держит основной рисунок личности и опирается на устойчивые "
        "детерминированные факты карты, а не на типологии или декоративные ярлыки.",
    ),
    "perception_and_mind": (
        "Мышление и восприятие",
        "Здесь раскрывается способ замечать детали, фильтровать смысл и собирать "
        "картину мира на основании конкретных связок Меркурия, воздуха и дома мышления.",
    ),
    "emotional_regulation": (
        "Эмоциональная регуляция",
        "Эта часть объясняет ритм чувств и внутреннюю переработку переживаний через "
        "Луну, водную чувствительность и факторы эмоциональной устойчивости.",
    ),
    "agency_and_desire": (
        "Воля и действие",
        "Здесь описан способ включаться в действие, выдерживать напряжение и "
        "проявлять инициативу без пересказа технической подложки нижнего слоя.",
    ),
    "relationships_and_intimacy": (
        "Близость и отношения",
        "Секция показывает, как выстраиваются доверие, близость и контакт, когда "
        "Венера, седьмой дом и relational факты собираются в один связный сюжет.",
    ),
    "growth_vector": (
        "Вектор роста",
        "Финальная секция собирает точки роста и способы интеграции напряжения так, "
        "чтобы отчёт завершался направлением развития, а не общими фразами.",
    ),
}


def build_smoke_report_bundle_v2() -> dict[str, Any]:
    """Build a fully ready deterministic+assembled sample bundle for QA gates."""

    chart_id = uuid.uuid4()
    facts = _sample_facts(chart_id)
    evidence = _sample_evidence(chart_id, facts)
    synthesis_row = build_natal_synthesis_row(
        chart_id=chart_id,
        facts=facts,
        facts_version="facts:v2-smoke",
        source_version=_SMOKE_SOURCE_VERSION,
    )
    outline_row = build_report_outline_row(
        synthesis=_synthesis_contract(chart_id, synthesis_row), source_version=_SMOKE_SOURCE_VERSION
    )
    infographic_row = build_natal_infographic_data_row(
        chart_id=chart_id,
        positions=_sample_positions(chart_id),
        houses=_sample_houses(chart_id),
        aspects=_sample_aspects(chart_id),
        balances=_sample_balances(chart_id),
        facts=facts,
        evidence=evidence,
        source_version=_SMOKE_SOURCE_VERSION,
    )
    segment_rows = _sample_segments(chart_id=chart_id, outline_row=outline_row, synthesis_row=synthesis_row)
    report_row = build_natal_report_row(
        chart_id=chart_id,
        synthesis_row=synthesis_row,
        outline_row=outline_row,
        infographic_row=infographic_row,
        segment_rows=segment_rows,
        previous_version=0,
    )
    if report_row.id is None:
        report_row.id = uuid.uuid4()
    report_row.status = "ready"
    progress = build_report_progress_v2(report=report_row, outline=outline_row, segments=segment_rows)
    fact_cards = _fact_cards(facts, evidence)
    report_payload = build_report_read_payload_v2(
        report=report_row,
        outline=outline_row,
        infographic=infographic_row,
        facts=fact_cards,
        segments=segment_rows,
    )
    report_id = str(report_row.id)
    return {
        "contract_version": "astrotype_v2_qa_smoke_bundle_v1",
        "chart_id": str(chart_id),
        "report_id": report_id,
        "report_status": progress["status"],
        "assembled_contract": report_row.assembled_payload.get("contract_version"),
        "infographic_contract": infographic_row.calculation_layer.get("contract_version"),
        "outline_contract": outline_row.outline.get("contract_version"),
        "progress": progress,
        "report_payload": report_payload,
        "report_row": {
            "status": report_row.status,
            "version": report_row.version,
        },
        "segment_statuses": {segment.section_key: segment.status for segment in segment_rows},
        "total_segments": len(segment_rows),
        "ready_segments": sum(1 for segment in segment_rows if segment.status == "ready"),
        "evidence_fact_keys": sorted(fact.fact_key for fact in facts),
        "fact_cards": fact_cards,
        "client_report_ids": {
            "web": report_id,
            "android_pwa": report_id,
            "desktop_optional": report_id,
        },
        "client_endpoints": {
            "web": f"/app/reports/{report_id}",
            "android_pwa": f"/m/reports/{report_id}",
            "desktop_optional": f"/desktop/reports/{report_id}",
        },
        "observability": build_rollout_observability_checklist(),
        "forbidden_hits": _forbidden_hits(
            (report_payload, outline_row.outline, infographic_row.calculation_layer, [s.payload for s in segment_rows])
        ),
    }


def validate_v2_smoke_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """Return explicit rollout-gate checks for the QA smoke bundle."""

    progress = bundle["progress"]
    report_payload = bundle["report_payload"]
    report_sections = report_payload["report"]["narrative_payload"]["sections"]
    report_evidence_ids = sorted(
        {evidence_id for section in report_sections for evidence_id in section["evidence_ids"]}
    )
    visible_fact_keys = sorted(card["fact_key"] for card in bundle["fact_cards"])
    fact_key_by_evidence_id = {
        source["payload"].get("evidence_id"): card["fact_key"]
        for card in bundle["fact_cards"]
        for source in card["sources"]
        if source["payload"].get("evidence_id")
    }
    evidence_fact_keys = sorted({fact_key_by_evidence_id[evidence_id] for evidence_id in report_evidence_ids})
    client_report_ids = bundle["client_report_ids"]
    report_id = bundle["report_id"]
    client_report_id_values = list(client_report_ids.values())
    checks = {
        "actual_report_readiness": (
            bundle["report_row"]["status"] == "ready"
            and progress["status"] == "ready"
            and bundle["ready_segments"] == bundle["total_segments"]
            and report_payload["report"]["assembled_payload"]["contract_version"] == "natal_report_v2"
        ),
        "not_infra_health_only": progress["status"] == "ready" and bool(report_sections),
        "facts_match_report_evidence_ids": evidence_fact_keys == visible_fact_keys,
        "infographics_from_deterministic_data": (
            bundle["infographic_contract"] == "natal_infographic_data_v2"
            and report_payload["infographic"]["calculation_layer"]
            == report_payload["report"]["deterministic_payload"]["technical_basis"]["calculation_layer"]
        ),
        "no_excluded_typology_leakage": bundle["forbidden_hits"] == [],
        "multi_client_same_report_id": set(client_report_id_values) == {report_id},
    }
    return {
        "report_status": progress["status"],
        "assembled_contract": report_payload["report"]["assembled_payload"]["contract_version"],
        "infographic_contract": bundle["infographic_contract"],
        "report_id": report_id,
        "client_report_ids": client_report_id_values,
        "client_endpoints": bundle["client_endpoints"],
        "total_segments": bundle["total_segments"],
        "ready_segments": bundle["ready_segments"],
        "evidence_fact_keys": evidence_fact_keys,
        "forbidden_hits": bundle["forbidden_hits"],
        "checks": checks,
    }


def simulate_failed_segment_recovery_v2() -> dict[str, Any]:
    """Return a deterministic example showing section-only retry recovery."""

    before = {
        "status": "failed",
        "failed_section": "emotional_regulation",
        "retry_scope": "section_only",
        "ready_segments": 5,
        "total_segments": 6,
    }
    after = {
        "status": "ready",
        "retried_section": "emotional_regulation",
        "retry_scope": "section_only",
        "ready_segments": 6,
        "total_segments": 6,
    }
    return {"before": before, "after": after}


def build_rollout_observability_checklist() -> list[str]:
    """Return rollout metrics/checklist items that must exist for v2 launch."""

    return [
        "llm_cost_by_segment",
        "llm_latency_by_segment",
        "llm_failures_by_segment",
        "generation_recovery_rate",
        "report_ready_latency",
        "rollback_to_previous_main_sha",
    ]


def _sample_positions(chart_id: uuid.UUID) -> list[models.NatalPlanetPosition]:
    return [
        models.NatalPlanetPosition(
            chart_id=chart_id,
            body="Sun",
            longitude=15.2,
            latitude=0.0,
            speed=0.95,
            sign="Aries",
            sign_degree=15.2,
            house_number=1,
            retrograde=False,
        ),
        models.NatalPlanetPosition(
            chart_id=chart_id,
            body="Moon",
            longitude=102.4,
            latitude=0.0,
            speed=13.4,
            sign="Cancer",
            sign_degree=12.4,
            house_number=4,
            retrograde=False,
        ),
        models.NatalPlanetPosition(
            chart_id=chart_id,
            body="Ascendant",
            longitude=213.1,
            latitude=0.0,
            speed=None,
            sign="Scorpio",
            sign_degree=3.1,
            house_number=1,
            retrograde=False,
        ),
        models.NatalPlanetPosition(
            chart_id=chart_id,
            body="Mercury",
            longitude=43.0,
            latitude=0.0,
            speed=1.2,
            sign="Taurus",
            sign_degree=13.0,
            house_number=3,
            retrograde=False,
        ),
        models.NatalPlanetPosition(
            chart_id=chart_id,
            body="Venus",
            longitude=351.8,
            latitude=0.0,
            speed=1.1,
            sign="Pisces",
            sign_degree=21.8,
            house_number=7,
            retrograde=False,
        ),
        models.NatalPlanetPosition(
            chart_id=chart_id,
            body="Mars",
            longitude=289.4,
            latitude=0.0,
            speed=0.7,
            sign="Capricorn",
            sign_degree=19.4,
            house_number=10,
            retrograde=False,
        ),
        models.NatalPlanetPosition(
            chart_id=chart_id,
            body="Jupiter",
            longitude=154.0,
            latitude=0.0,
            speed=0.2,
            sign="Virgo",
            sign_degree=4.0,
            house_number=11,
            retrograde=False,
        ),
        models.NatalPlanetPosition(
            chart_id=chart_id,
            body="Saturn",
            longitude=187.2,
            latitude=0.0,
            speed=0.1,
            sign="Libra",
            sign_degree=7.2,
            house_number=12,
            retrograde=True,
        ),
    ]


def _sample_houses(chart_id: uuid.UUID) -> list[models.NatalHouse]:
    signs = [
        "Scorpio",
        "Sagittarius",
        "Capricorn",
        "Aquarius",
        "Pisces",
        "Aries",
        "Taurus",
        "Gemini",
        "Cancer",
        "Leo",
        "Virgo",
        "Libra",
    ]
    return [
        models.NatalHouse(chart_id=chart_id, house_number=index + 1, longitude=float(index * 30), sign=sign)
        for index, sign in enumerate(signs)
    ]


def _sample_aspects(chart_id: uuid.UUID) -> list[models.NatalAspect]:
    return [
        models.NatalAspect(
            chart_id=chart_id,
            body_a="Sun",
            body_b="Moon",
            aspect_code="square",
            angle_degrees=90.0,
            orb_degrees=2.1,
            applying=True,
            strength=0.82,
        ),
        models.NatalAspect(
            chart_id=chart_id,
            body_a="Mercury",
            body_b="Mars",
            aspect_code="trine",
            angle_degrees=120.0,
            orb_degrees=1.4,
            applying=False,
            strength=0.91,
        ),
        models.NatalAspect(
            chart_id=chart_id,
            body_a="Venus",
            body_b="Saturn",
            aspect_code="sextile",
            angle_degrees=60.0,
            orb_degrees=1.2,
            applying=True,
            strength=0.88,
        ),
        models.NatalAspect(
            chart_id=chart_id,
            body_a="Moon",
            body_b="Venus",
            aspect_code="trine",
            angle_degrees=120.0,
            orb_degrees=3.0,
            applying=False,
            strength=0.72,
        ),
        models.NatalAspect(
            chart_id=chart_id,
            body_a="Mars",
            body_b="Saturn",
            aspect_code="conjunction",
            angle_degrees=0.0,
            orb_degrees=4.4,
            applying=True,
            strength=0.63,
        ),
    ]


def _sample_balances(chart_id: uuid.UUID) -> list[models.NatalChartBalance]:
    return [
        models.NatalChartBalance(chart_id=chart_id, category="elements", key="fire", value=34.0, rank=1),
        models.NatalChartBalance(chart_id=chart_id, category="elements", key="water", value=26.0, rank=2),
        models.NatalChartBalance(chart_id=chart_id, category="elements", key="earth", value=24.0, rank=3),
        models.NatalChartBalance(chart_id=chart_id, category="elements", key="air", value=16.0, rank=4),
        models.NatalChartBalance(chart_id=chart_id, category="modalities", key="cardinal", value=42.0, rank=1),
        models.NatalChartBalance(chart_id=chart_id, category="modalities", key="fixed", value=33.0, rank=2),
        models.NatalChartBalance(chart_id=chart_id, category="modalities", key="mutable", value=25.0, rank=3),
    ]


def _sample_facts(chart_id: uuid.UUID) -> list[models.NatalFact]:
    return [
        _fact(
            chart_id,
            "placement:sun:aries:house_1",
            "Солнечное ядро в Овне и 1 доме",
            "Личность проявляется прямо и заметно, с быстрым выходом в действие.",
            0.95,
            "resource",
            "placements",
            "ev:core:sun",
        ),
        _fact(
            chart_id,
            "placement:mercury:taurus:house_3",
            "Меркурий в Тельце и 3 доме",
            "Мышление движется через медленную проверку смысла и опору на факты.",
            0.84,
            "resource",
            "mind",
            "ev:mind:mercury",
        ),
        _fact(
            chart_id,
            "placement:moon:cancer:house_4",
            "Луна в Раке и 4 доме",
            "Чувства глубоко связаны с безопасностью, памятью и домашней средой.",
            0.88,
            "resource",
            "emotional",
            "ev:emotion:moon",
        ),
        _fact(
            chart_id,
            "placement:mars:capricorn:house_10",
            "Марс в Козероге и 10 доме",
            "Воля лучше всего раскрывается через собранность, цель и управляемое усилие.",
            0.9,
            "resource",
            "agency",
            "ev:agency:mars",
        ),
        _fact(
            chart_id,
            "placement:venus:pisces:house_7",
            "Венера в Рыбах и 7 доме",
            "В отношениях высока чувствительность к тону контакта и эмоциональной взаимности.",
            0.86,
            "resource",
            "relationships",
            "ev:relationships:venus",
        ),
        _fact(
            chart_id,
            "aspect:sun:moon:square",
            "Квадрат Солнца и Луны",
            "Рост требует согласовать импульс действия с эмоциональным ритмом, а не вытеснять одно другим.",
            0.82,
            "growth",
            "growth",
            "ev:growth:sun-moon",
        ),
    ]


def _fact(
    chart_id: uuid.UUID,
    fact_key: str,
    title: str,
    summary: str,
    weight: float,
    polarity: str,
    section_hint: str,
    evidence_id: str,
) -> models.NatalFact:
    return models.NatalFact(
        chart_id=chart_id,
        fact_type="aspect" if fact_key.startswith("aspect:") else "placement",
        fact_key=fact_key,
        title=title,
        summary=summary,
        weight=weight,
        confidence=0.93,
        polarity=polarity,
        section_hint=section_hint,
        payload={"evidence_ids": [evidence_id]},
        source_version=_SMOKE_SOURCE_VERSION,
    )


def _sample_evidence(chart_id: uuid.UUID, facts: list[models.NatalFact]) -> list[models.NatalFactEvidence]:
    evidence_rows: list[models.NatalFactEvidence] = []
    for fact in facts:
        evidence_id = str(fact.payload["evidence_ids"][0])
        fact.id = uuid.uuid4()
        evidence_rows.append(
            models.NatalFactEvidence(
                fact_id=fact.id,
                chart_id=chart_id,
                source_table="astrotype_v2_natal_facts",
                source_id=fact.id,
                source_key=f"fact:{fact.fact_key}",
                payload={"evidence_id": evidence_id, "fact_key": fact.fact_key},
            )
        )
    return evidence_rows


def _sample_segments(
    *,
    chart_id: uuid.UUID,
    outline_row: models.ReportOutline,
    synthesis_row: models.NatalSynthesis,
) -> list[models.ReportSegmentGeneration]:
    theme_by_id = {theme["id"]: theme for theme in synthesis_row.payload["dominant_themes"]}
    rows: list[models.ReportSegmentGeneration] = []
    for section in outline_row.outline["sections"]:
        section_id = str(section["id"])
        theme_ids = list(section["owned_theme_ids"])
        evidence_ids = sorted(
            {evidence_id for theme_id in theme_ids for evidence_id in theme_by_id[theme_id]["evidence_ids"]}
        )
        title, body = _SECTION_COPY[section_id]
        response = ReportSegmentOutputV2(
            section_id=section_id,
            title=title,
            body=body,
            covered_theme_ids=theme_ids,
            evidence_ids=evidence_ids,
        ).model_dump(mode="json")
        rows.append(
            models.ReportSegmentGeneration(
                chart_id=chart_id,
                outline_id=outline_row.id,
                section_key=section_id,
                status="ready",
                provider="smoke-provider",
                model="smoke-model",
                prompt_version="astrotype_v2_segment_v1",
                payload={
                    "request": {
                        "section_id": section_id,
                        "owned_theme_ids": theme_ids,
                        "evidence_ids": evidence_ids,
                    },
                    "request_hash": f"request:{section_id}",
                    "prompt_hash": f"prompt:{section_id}",
                    "response": response,
                    "response_hash": f"response:{section_id}",
                    "retry_scope": "section_only",
                    "continuation": {"required": False, "cursor": None, "next_request_scope": None},
                },
                error=None,
            )
        )
    return rows


def _fact_cards(
    facts: list[models.NatalFact],
    evidence: list[models.NatalFactEvidence],
) -> list[dict[str, Any]]:
    evidence_by_fact_id = {row.fact_id: row for row in evidence}
    return [
        {
            "fact_key": fact.fact_key,
            "title": fact.title,
            "summary": fact.summary,
            "sources": [
                {
                    "source_table": evidence_by_fact_id[fact.id].source_table,
                    "source_key": evidence_by_fact_id[fact.id].source_key,
                    "payload": evidence_by_fact_id[fact.id].payload,
                }
            ],
        }
        for fact in sorted(facts, key=lambda row: row.fact_key)
    ]


def _forbidden_hits(payloads: Iterable[Any]) -> list[str]:
    serialized = json.dumps(list(payloads), ensure_ascii=False, sort_keys=True).lower()
    return [token for token in _FORBIDDEN_TYPOLOGY_TOKENS if token in serialized]


def _synthesis_contract(chart_id: uuid.UUID, row: models.NatalSynthesis) -> Any:
    class _SynthesisContract:
        def __init__(self, chart_id: uuid.UUID, payload: dict[str, Any]) -> None:
            self.chart_id = chart_id
            self.payload = payload
            self.dominant_themes = tuple(payload["dominant_themes"])

    class _Theme(dict[str, Any]):
        @property
        def id(self) -> str:
            return str(self["id"])

        @property
        def primary_section(self) -> str:
            return _primary_section_from_theme_id(self.id)

        @property
        def evidence_ids(self) -> tuple[str, ...]:
            return tuple(self["evidence_ids"])

        @property
        def weight(self) -> float:
            return float(self["weight"])

        @property
        def title(self) -> str:
            return str(self["title"])

    contract = _SynthesisContract(chart_id, row.payload)
    contract.dominant_themes = tuple(_Theme(theme) for theme in row.payload["dominant_themes"])
    return contract


def _primary_section_from_theme_id(theme_id: str) -> str:
    if ":mind:" in theme_id:
        return "perception_and_mind"
    if ":emotional:" in theme_id:
        return "emotional_regulation"
    if ":agency:" in theme_id:
        return "agency_and_desire"
    if ":relationships:" in theme_id:
        return "relationships_and_intimacy"
    if ":growth:" in theme_id:
        return "growth_vector"
    return "core_pattern"
