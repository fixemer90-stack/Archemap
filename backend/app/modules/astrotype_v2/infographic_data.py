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
    aspect_table = [_aspect_table_row(aspect) for aspect in aspect_rows]
    aspect_edges = [_aspect_network_edge(aspect) for aspect in aspect_rows]
    positions_with_aspects = _attach_sampled_aspects(position_payloads, aspect_table)
    house_accents = _house_accents(house_payloads, positions_with_aspects)
    return {
        "contract_version": INFOGRAPHIC_CONTRACT_VERSION,
        "chart_id": str(chart_id),
        "reader_blocks": [
            "key_indicators",
            "planet_positions",
            "balance_bars",
            "house_emphasis",
            "aspect_network",
            "key_aspects",
            "calculation_matrix",
        ],
        "key_indicators": _key_indicators(positions=positions_with_aspects, houses=house_payloads),
        "planet_positions": positions_with_aspects,
        "balance_bars": _balance_bars(balance_payloads),
        "house_emphasis": _house_emphasis(house_accents),
        "aspect_network": {"nodes": _aspect_nodes(positions_with_aspects), "edges": aspect_edges},
        "key_aspects": aspect_table,
        "calculation_matrix": _calculation_matrix(
            positions=positions,
            houses=houses,
            aspects=aspects,
            facts=facts,
            balances=balances,
        ),
        "house_accents": house_accents,
        "aspect_table": aspect_table,
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


def _key_indicators(
    *, positions: list[dict[str, Any]], houses: list[dict[str, Any]]
) -> dict[str, dict[str, Any] | None]:
    by_body = {str(position["body"]).lower(): position for position in positions}
    ascendant = by_body.get("ascendant")
    mc = by_body.get("mc") or _mc_from_houses(houses)
    ruler = _ascendant_ruler(ascendant=ascendant, by_body=by_body)
    return {
        "sun": by_body.get("sun"),
        "moon": by_body.get("moon"),
        "ascendant": ascendant,
        "mc": mc,
        "ascendant_ruler": ruler,
    }


def _mc_from_houses(houses: list[dict[str, Any]]) -> dict[str, Any] | None:
    house_ten = next((house for house in houses if house.get("house_number") == 10), None)
    if house_ten is None:
        return None
    return {
        "body": "MC",
        "longitude": house_ten.get("longitude"),
        "sign": house_ten.get("sign"),
        "sign_degree": None,
        "degree_label": f"MC · {house_ten.get('sign')}",
        "house_number": 10,
        "retrograde": False,
    }


def _ascendant_ruler(*, ascendant: dict[str, Any] | None, by_body: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if ascendant is None:
        return None
    ruler_body = _SIGN_RULERS.get(str(ascendant.get("sign")))
    if ruler_body is None:
        return None
    ruler_position = by_body.get(ruler_body.lower())
    return {"planet": ruler_body, "position": ruler_position}


_SIGN_RULERS = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}


def _attach_sampled_aspects(
    positions: list[dict[str, Any]], aspect_table: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    aspects_by_body: dict[str, list[dict[str, Any]]] = {}
    for aspect in aspect_table:
        for body_key in ("body_a", "body_b"):
            body = str(aspect[body_key])
            aspects_by_body.setdefault(body, []).append(aspect)
    return [
        {
            **position,
            "sampled_aspects": sorted(
                aspects_by_body.get(str(position["body"]), []),
                key=lambda row: (row["orb_degrees"], row["body_a"], row["body_b"]),
            )[:3],
        }
        for position in positions
    ]


def _balance_bars(balance_payloads: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for balance in balance_payloads:
        grouped.setdefault(str(balance["category"]), []).append(balance)
    return {
        category: sorted(rows, key=lambda row: (row.get("rank") or 999, row["key"]))
        for category, rows in grouped.items()
    }


def _house_emphasis(house_accents: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    bars = sorted(house_accents, key=lambda row: int(row["house_number"]))
    top_houses = sorted(bars, key=lambda row: (-int(row["accent_weight"]), int(row["house_number"])))[:3]
    return {"bars": bars, "top_houses": top_houses}


def _aspect_nodes(positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": position["body"],
            "label": position["body"],
            "sign": position.get("sign"),
            "house_number": position.get("house_number"),
        }
        for position in positions
    ]


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
        "house_mode": _house_mode_summary(positions),
        "hemispheres": _hemisphere_summary(positions),
        "quadrants": _quadrant_summary(positions),
        "aspect_profile": _aspect_profile(aspects),
        "balance_categories": sorted({balance.category for balance in balances}),
        "fact_types": sorted({fact.fact_type for fact in facts}),
    }


def _house_mode_summary(positions: Sequence[models.NatalPlanetPosition]) -> dict[str, int]:
    modes = {"angular": {1, 4, 7, 10}, "succedent": {2, 5, 8, 11}, "cadent": {3, 6, 9, 12}}
    return {
        mode: sum(1 for position in positions if position.house_number in house_numbers)
        for mode, house_numbers in modes.items()
    }


def _hemisphere_summary(positions: Sequence[models.NatalPlanetPosition]) -> dict[str, int]:
    return {
        "upper": sum(1 for position in positions if position.house_number in {7, 8, 9, 10, 11, 12}),
        "lower": sum(1 for position in positions if position.house_number in {1, 2, 3, 4, 5, 6}),
        "eastern": sum(1 for position in positions if position.house_number in {10, 11, 12, 1, 2, 3}),
        "western": sum(1 for position in positions if position.house_number in {4, 5, 6, 7, 8, 9}),
    }


def _quadrant_summary(positions: Sequence[models.NatalPlanetPosition]) -> dict[str, int]:
    quadrants = {"q1": {1, 2, 3}, "q2": {4, 5, 6}, "q3": {7, 8, 9}, "q4": {10, 11, 12}}
    return {
        quadrant: sum(1 for position in positions if position.house_number in house_numbers)
        for quadrant, house_numbers in quadrants.items()
    }


def _aspect_profile(aspects: Sequence[models.NatalAspect]) -> dict[str, Any]:
    tension = {"square", "opposition", "quincunx"}
    resource = {"trine", "sextile"}
    return {
        "counts": {
            "resource": sum(1 for aspect in aspects if aspect.aspect_code in resource),
            "tension": sum(1 for aspect in aspects if aspect.aspect_code in tension),
            "conjunction": sum(1 for aspect in aspects if aspect.aspect_code == "conjunction"),
        },
        "average_orb_degrees": round(sum(float(aspect.orb_degrees) for aspect in aspects) / len(aspects), 2)
        if aspects
        else None,
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
