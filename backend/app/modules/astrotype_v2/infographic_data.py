"""Deterministic lower calculation-layer payloads for Astrotype v2 reports."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from app.modules.astrotype_v2 import models

INFOGRAPHIC_CONTRACT_VERSION = "natal_infographic_data_v2"
INFOGRAPHIC_API_CONTRACT_VERSION = "natal_infographic_api_v2"


def build_natal_infographic_data_v2(
    *,
    chart_id: uuid.UUID,
    positions: Sequence[models.NatalPlanetPosition],
    houses: Sequence[models.NatalHouse],
    aspects: Sequence[models.NatalAspect],
    balances: Sequence[models.NatalChartBalance],
    facts: Sequence[models.NatalFact],
    evidence: Sequence[models.NatalFactEvidence],
) -> dict[str, Any]:
    """Build web/mobile-ready deterministic visual data from stored v2 rows."""

    position_payloads = [_position_payload(position) for position in sorted(positions, key=_position_sort_key)]
    house_payloads = [_house_payload(house) for house in sorted(houses, key=lambda row: row.house_number)]
    balance_payloads = [_balance_payload(balance) for balance in sorted(balances, key=_balance_sort_key)]
    aspect_rows = sorted(aspects, key=lambda row: (row.body_a, row.body_b, row.aspect_code))
    return {
        "contract_version": INFOGRAPHIC_CONTRACT_VERSION,
        "chart_id": str(chart_id),
        "key_indicators": _key_indicators(position_payloads),
        "planet_positions": position_payloads,
        "balance_bars": balance_payloads,
        "house_accents": _house_accents(house_payloads, position_payloads),
        "aspect_network": [_aspect_network_edge(aspect) for aspect in aspect_rows],
        "aspect_table": [_aspect_table_row(aspect) for aspect in aspect_rows],
        "calculation_matrix": _calculation_matrix(
            positions=positions,
            houses=houses,
            aspects=aspects,
            facts=facts,
            balances=balances,
        ),
        "evidence_cards": build_evidence_cards_v2(facts=facts, evidence=evidence),
        "progressive_disclosure": {
            "mode": "compact_inline",
            "summary": "Evidence/provenance is available per calculation item on demand.",
        },
    }


def build_evidence_cards_v2(
    *,
    facts: Sequence[models.NatalFact],
    evidence: Sequence[models.NatalFactEvidence],
) -> list[dict[str, Any]]:
    """Build compact fact cards for progressive disclosure under calculation items."""

    _reject_non_v2_evidence(evidence)
    evidence_by_fact_id: dict[uuid.UUID, list[models.NatalFactEvidence]] = {}
    indexed_unsaved_evidence: dict[int, list[models.NatalFactEvidence]] = {}
    for index, evidence_row in enumerate(evidence):
        if evidence_row.fact_id is None:
            indexed_unsaved_evidence.setdefault(index, []).append(evidence_row)
        else:
            evidence_by_fact_id.setdefault(evidence_row.fact_id, []).append(evidence_row)

    indexed_facts = list(enumerate(facts))
    return [
        _evidence_card(
            fact,
            indexed_unsaved_evidence.get(index, []) if fact.id is None else evidence_by_fact_id.get(fact.id, []),
        )
        for index, fact in sorted(indexed_facts, key=lambda item: _fact_sort_key(item[1]))
    ]


def build_infographic_api_payload_v2(
    *,
    chart_id: uuid.UUID,
    source_version: str,
    calculation_layer: dict[str, Any],
    evidence_cards: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return reusable deterministic payload shape for web and Android clients."""

    return {
        "contract_version": INFOGRAPHIC_API_CONTRACT_VERSION,
        "chart_id": str(chart_id),
        "source_version": source_version,
        "calculation_layer": calculation_layer,
        "evidence_cards": evidence_cards,
    }


def build_natal_infographic_data_row(
    *,
    chart_id: uuid.UUID,
    positions: Sequence[models.NatalPlanetPosition],
    houses: Sequence[models.NatalHouse],
    aspects: Sequence[models.NatalAspect],
    balances: Sequence[models.NatalChartBalance],
    facts: Sequence[models.NatalFact],
    evidence: Sequence[models.NatalFactEvidence],
    source_version: str = "v2.0",
) -> models.NatalInfographicData:
    """Build a persistable v2 calculation-layer row without writing it."""

    return models.NatalInfographicData(
        chart_id=chart_id,
        status="ready",
        calculation_layer=build_natal_infographic_data_v2(
            chart_id=chart_id,
            positions=positions,
            houses=houses,
            aspects=aspects,
            balances=balances,
            facts=facts,
            evidence=evidence,
        ),
        source_version=source_version,
    )


def _reject_non_v2_evidence(evidence: Sequence[models.NatalFactEvidence]) -> None:
    for evidence_row in evidence:
        if not evidence_row.source_table.startswith("astrotype_v2_"):
            raise ValueError(f"non-v2 evidence source: {evidence_row.source_table}")


def _position_payload(row: models.NatalPlanetPosition) -> dict[str, Any]:
    return {
        "body": row.body,
        "longitude": row.longitude,
        "latitude": row.latitude,
        "speed": row.speed,
        "sign": row.sign,
        "sign_degree": row.sign_degree,
        "degree_label": f"{row.sign_degree:.2f}° {row.sign}",
        "house_number": row.house_number,
        "retrograde": row.retrograde,
    }


def _house_payload(row: models.NatalHouse) -> dict[str, Any]:
    return {"house_number": row.house_number, "longitude": row.longitude, "sign": row.sign}


def _balance_payload(row: models.NatalChartBalance) -> dict[str, Any]:
    return {"category": row.category, "key": row.key, "value": row.value, "rank": row.rank}


def _aspect_network_edge(row: models.NatalAspect) -> dict[str, Any]:
    return {
        "source": row.body_a,
        "target": row.body_b,
        "aspect_code": row.aspect_code,
        "strength": row.strength,
        "orb_degrees": row.orb_degrees,
        "applying": row.applying,
    }


def _aspect_table_row(row: models.NatalAspect) -> dict[str, Any]:
    return {
        "body_a": row.body_a,
        "body_b": row.body_b,
        "aspect_code": row.aspect_code,
        "angle_degrees": row.angle_degrees,
        "orb_degrees": row.orb_degrees,
        "applying": row.applying,
        "strength": row.strength,
    }


def _key_indicators(position_payloads: list[dict[str, Any]]) -> dict[str, dict[str, Any] | None]:
    by_body = {str(position["body"]).lower(): position for position in position_payloads}
    return {"sun": by_body.get("sun"), "moon": by_body.get("moon"), "ascendant": by_body.get("ascendant")}


def _house_accents(
    house_payloads: list[dict[str, Any]], position_payloads: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    body_counts_by_house: dict[int, int] = {}
    for position in position_payloads:
        house_number = position.get("house_number")
        if isinstance(house_number, int):
            body_counts_by_house[house_number] = body_counts_by_house.get(house_number, 0) + 1
    return [
        {
            **house,
            "body_count": body_counts_by_house.get(int(house["house_number"]), 0),
            "accent_weight": body_counts_by_house.get(int(house["house_number"]), 0),
        }
        for house in house_payloads
    ]


def _calculation_matrix(
    *,
    positions: Sequence[models.NatalPlanetPosition],
    houses: Sequence[models.NatalHouse],
    aspects: Sequence[models.NatalAspect],
    facts: Sequence[models.NatalFact],
    balances: Sequence[models.NatalChartBalance],
) -> dict[str, Any]:
    return {
        "counts": {
            "positions": len(positions),
            "houses": len(houses),
            "aspects": len(aspects),
            "facts": len(facts),
        },
        "balance_categories": sorted({balance.category for balance in balances}),
        "fact_types": sorted({fact.fact_type for fact in facts}),
    }


def _evidence_card(fact: models.NatalFact, evidence_rows: Sequence[models.NatalFactEvidence]) -> dict[str, Any]:
    return {
        "fact_key": fact.fact_key,
        "title": fact.title,
        "summary": fact.summary,
        "fact_type": fact.fact_type,
        "section_usage": [fact.section_hint] if fact.section_hint else [],
        "technical_value": fact.payload,
        "weight": fact.weight,
        "confidence": fact.confidence,
        "badge": fact.polarity or fact.fact_type,
        "sources": [_source_payload(row) for row in sorted(evidence_rows, key=lambda row: row.source_key or "")],
    }


def _source_payload(row: models.NatalFactEvidence) -> dict[str, Any]:
    return {
        "source_table": row.source_table,
        "source_id": str(row.source_id) if row.source_id is not None else None,
        "source_key": row.source_key,
        "payload": row.payload,
    }


def _position_sort_key(row: models.NatalPlanetPosition) -> tuple[int, str]:
    order = {"Sun": 0, "Moon": 1, "Ascendant": 2}
    return (order.get(row.body, 100), row.body)


def _balance_sort_key(row: models.NatalChartBalance) -> tuple[str, int, str]:
    return (row.category, row.rank if row.rank is not None else 999, row.key)


def _fact_sort_key(row: models.NatalFact) -> tuple[int, float, str]:
    order = {"placement": 0, "balance": 1, "pattern": 2, "aspect": 3}
    return (order.get(row.fact_type, 100), -row.weight, row.fact_key)
