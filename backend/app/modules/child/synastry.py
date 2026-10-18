"""Deterministic pair-specific synastry evidence from persisted chart longitudes."""

from __future__ import annotations

from collections.abc import Sequence
from math import isfinite
from typing import Any
from uuid import UUID

from app.modules.astrotype_v2.models import NatalChart, NatalHouse, NatalPlanetPosition
from app.modules.child.child_needs import _valid_confidence_provenance
from app.modules.child.interaction_identity import synastry_evidence_id
from app.modules.child.models import ChildChartVersion, ChildSynastryEvidence
from app.modules.child.parent_style import _has_exact_timing_proof
from app.modules.child.scoring.types import InteractionDimension
from app.reference_data.child.interaction_v1 import (
    ANGLE_BODIES,
    ASPECT_CATALOG,
    HOUSE_OVERLAY_DEFINITIONS,
    HOUSE_OVERLAY_WEIGHT,
    JUPITER_DIMENSIONS,
    PERSONAL_BODIES,
    SATURN_DIMENSIONS,
    SYNASTRY_REFERENCE_VERSION,
    SYNASTRY_RULES,
    SynastryRule,
)


def build_synastry_evidence(
    *,
    child_profile_id: UUID,
    generation_id: UUID,
    parent_chart: NatalChart,
    parent_positions: Sequence[NatalPlanetPosition],
    child_chart: ChildChartVersion,
    parent_houses: Sequence[NatalHouse] = (),
) -> tuple[ChildSynastryEvidence, ...]:
    """Build canonical allowed cross-chart aspects and fail closed on provenance conflicts."""

    parent = _canonical_parent_positions(parent_positions, chart_id=parent_chart.id)
    child = _canonical_child_positions(child_chart)
    if child is None:
        return ()
    parent_exact = _has_exact_timing_proof(parent_chart)
    child_exact = child_chart.birth_time_confidence == "exact"
    if not parent_exact:
        parent.pop("moon", None)
    if not child_exact:
        child.pop("moon", None)

    rows: dict[str, ChildSynastryEvidence] = {}
    for parent_body, parent_longitude in sorted(parent.items()):
        for child_body, child_longitude in sorted(child.items()):
            rule = _rule_for_pair(parent_body, child_body)
            if rule is None:
                continue
            aspect = _resolve_aspect(parent_longitude, child_longitude)
            if aspect is None:
                continue
            definition, orb = aspect
            strength = round(max(0.0, 1.0 - orb / definition.orb), 6)
            magnitude = rule.weight * strength
            if rule.saturn_bounded:
                magnitude = min(magnitude, 0.08)
            contribution = round(definition.direction * magnitude, 6)
            source_key = f"cross_aspect:parent_{parent_body}:child_{child_body}:{definition.code}"
            payload = {
                "reference_version": SYNASTRY_REFERENCE_VERSION,
                "aspect_code": definition.code,
                "orb_degrees": round(orb, 6),
                "allowed_orb_degrees": definition.orb,
                "strength": strength,
                "correlation_family": rule.signal_family,
                "factor_label": rule.factor_label,
                "dimensions": [dimension.value for dimension in rule.dimensions],
                "parent_body": parent_body,
                "child_body": child_body,
                "parent_chart_id": str(parent_chart.id),
                "child_chart_version_id": str(child_chart.id),
                "generation_id": str(generation_id),
                "child_profile_id": str(child_profile_id),
                "parent_source_ref": f"astrotype_v2_natal_planet_positions:key:{parent_body}",
                "child_source_ref": f"child_chart_versions:key:planet_positions:{child_body}",
                "time_reliable_for_overlays": parent_exact and child_exact,
            }
            row = ChildSynastryEvidence(
                id=synastry_evidence_id(
                    child_profile_id=child_profile_id,
                    generation_id=generation_id,
                    parent_chart_id=parent_chart.id,
                    child_chart_version_id=child_chart.id,
                    reference_version=SYNASTRY_REFERENCE_VERSION,
                    source_key=source_key,
                ),
                child_profile_id=child_profile_id,
                parent_chart_id=parent_chart.id,
                child_chart_version_id=child_chart.id,
                generation_id=generation_id,
                source_type="cross_chart_aspect",
                source_key=source_key,
                reference_version=SYNASTRY_REFERENCE_VERSION,
                contribution=contribution,
                direction="supports" if contribution >= 0 else "counters",
                payload=payload,
            )
            existing = rows.get(source_key)
            if existing is not None and existing.payload != row.payload:
                raise ValueError("conflicting duplicate synastry evidence")
            rows[source_key] = row
    if parent_exact and child_exact:
        _add_angle_aspects(
            rows,
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            parent_chart=parent_chart,
            child_chart=child_chart,
            parent_positions=parent,
            child_positions=child,
        )
        parent_cusps = _canonical_parent_houses(parent_houses, chart_id=parent_chart.id)
        child_cusps = _canonical_child_houses(child_chart)
        if parent_cusps is not None and child_cusps is not None:
            _add_house_overlays(
                rows,
                child_profile_id=child_profile_id,
                generation_id=generation_id,
                parent_chart=parent_chart,
                child_chart=child_chart,
                parent_positions=parent,
                child_positions=child,
                parent_cusps=parent_cusps,
                child_cusps=child_cusps,
            )
    return tuple(rows[key] for key in sorted(rows))


def _add_angle_aspects(
    rows: dict[str, ChildSynastryEvidence],
    *,
    child_profile_id: UUID,
    generation_id: UUID,
    parent_chart: NatalChart,
    child_chart: ChildChartVersion,
    parent_positions: dict[str, float],
    child_positions: dict[str, float],
) -> None:
    pairs = [
        (parent_body, child_body, parent_longitude, child_longitude)
        for parent_body, parent_longitude in parent_positions.items()
        for child_body, child_longitude in child_positions.items()
        if (parent_body in ANGLE_BODIES and child_body in PERSONAL_BODIES)
        or (parent_body in PERSONAL_BODIES and child_body in ANGLE_BODIES)
    ]
    for parent_body, child_body, parent_longitude, child_longitude in sorted(pairs):
        aspect = _resolve_aspect(parent_longitude, child_longitude)
        if aspect is None:
            continue
        definition, orb = aspect
        strength = round(max(0.0, 1.0 - orb / definition.orb), 6)
        contribution = round(definition.direction * 0.06 * strength, 6)
        source_key = f"angle_aspect:parent_{parent_body}:child_{child_body}:{definition.code}"
        angle = parent_body if parent_body in ANGLE_BODIES else child_body
        body = child_body if parent_body in ANGLE_BODIES else parent_body
        payload = {
            "reference_version": SYNASTRY_REFERENCE_VERSION,
            "aspect_code": definition.code,
            "orb_degrees": round(orb, 6),
            "allowed_orb_degrees": definition.orb,
            "strength": strength,
            "correlation_family": f"angle:{angle}-{body}",
            "factor_label": "angle_contact_context",
            "dimensions": [InteractionDimension.COMMUNICATION_FIT.value, InteractionDimension.AUTONOMY_BALANCE.value],
            "parent_body": parent_body,
            "child_body": child_body,
            "parent_chart_id": str(parent_chart.id),
            "child_chart_version_id": str(child_chart.id),
            "generation_id": str(generation_id),
            "child_profile_id": str(child_profile_id),
            "parent_source_ref": f"astrotype_v2_natal_planet_positions:key:{parent_body}",
            "child_source_ref": f"child_chart_versions:key:planet_positions:{child_body}",
            "time_reliable_for_overlays": True,
        }
        rows[source_key] = ChildSynastryEvidence(
            id=synastry_evidence_id(
                child_profile_id=child_profile_id,
                generation_id=generation_id,
                parent_chart_id=parent_chart.id,
                child_chart_version_id=child_chart.id,
                reference_version=SYNASTRY_REFERENCE_VERSION,
                source_key=source_key,
            ),
            child_profile_id=child_profile_id,
            parent_chart_id=parent_chart.id,
            child_chart_version_id=child_chart.id,
            generation_id=generation_id,
            source_type="angle_aspect",
            source_key=source_key,
            reference_version=SYNASTRY_REFERENCE_VERSION,
            contribution=contribution,
            direction="supports" if contribution >= 0 else "counters",
            payload=payload,
        )


def _add_house_overlays(
    rows: dict[str, ChildSynastryEvidence],
    *,
    child_profile_id: UUID,
    generation_id: UUID,
    parent_chart: NatalChart,
    child_chart: ChildChartVersion,
    parent_positions: dict[str, float],
    child_positions: dict[str, float],
    parent_cusps: tuple[float, ...],
    child_cusps: tuple[float, ...],
) -> None:
    definitions = {item.house_number: item for item in HOUSE_OVERLAY_DEFINITIONS}
    overlay_inputs = (
        ("child_in_parent", child_positions, parent_cusps),
        ("parent_in_child", parent_positions, child_cusps),
    )
    for overlay_direction, positions, cusps in overlay_inputs:
        for body, longitude in sorted(positions.items()):
            if body not in PERSONAL_BODIES:
                continue
            house_number = _house_for_longitude(longitude, cusps)
            definition = definitions.get(house_number)
            if definition is None:
                continue
            contribution = round(definition.direction * HOUSE_OVERLAY_WEIGHT, 6)
            source_key = f"house_overlay:{overlay_direction}:{body}:house_{house_number}"
            body_ref = (
                f"child_chart_versions:key:planet_positions:{body}"
                if overlay_direction == "child_in_parent"
                else f"astrotype_v2_natal_planet_positions:key:{body}"
            )
            house_ref = (
                f"astrotype_v2_natal_houses:key:{house_number}"
                if overlay_direction == "child_in_parent"
                else f"child_chart_versions:key:houses:{house_number}"
            )
            payload = {
                "reference_version": SYNASTRY_REFERENCE_VERSION,
                "strength": 1.0,
                "correlation_family": f"overlay:{overlay_direction}",
                "factor_label": definition.factor_label,
                "dimensions": [dimension.value for dimension in definition.dimensions],
                "overlay_direction": overlay_direction,
                "body": body,
                "house_number": house_number,
                "parent_chart_id": str(parent_chart.id),
                "child_chart_version_id": str(child_chart.id),
                "generation_id": str(generation_id),
                "child_profile_id": str(child_profile_id),
                "parent_source_ref": body_ref if overlay_direction == "parent_in_child" else house_ref,
                "child_source_ref": house_ref if overlay_direction == "parent_in_child" else body_ref,
                "time_reliable_for_overlays": True,
            }
            rows[source_key] = ChildSynastryEvidence(
                id=synastry_evidence_id(
                    child_profile_id=child_profile_id,
                    generation_id=generation_id,
                    parent_chart_id=parent_chart.id,
                    child_chart_version_id=child_chart.id,
                    reference_version=SYNASTRY_REFERENCE_VERSION,
                    source_key=source_key,
                ),
                child_profile_id=child_profile_id,
                parent_chart_id=parent_chart.id,
                child_chart_version_id=child_chart.id,
                generation_id=generation_id,
                source_type="house_overlay",
                source_key=source_key,
                reference_version=SYNASTRY_REFERENCE_VERSION,
                contribution=contribution,
                direction="supports" if contribution >= 0 else "counters",
                payload=payload,
            )


def _canonical_parent_positions(positions: Sequence[NatalPlanetPosition], *, chart_id: UUID) -> dict[str, float]:
    canonical: dict[str, float] = {}
    for row in positions:
        if row.chart_id != chart_id:
            raise ValueError("parent position references another chart")
        body = _body(row.body)
        longitude = _longitude(row.longitude)
        existing = canonical.get(body)
        if existing is not None and existing != longitude:
            raise ValueError("conflicting duplicate parent position")
        canonical[body] = longitude
    return canonical


def _canonical_child_positions(chart: ChildChartVersion) -> dict[str, float] | None:
    payload = chart.calculation_payload
    if not isinstance(payload, dict) or not _valid_confidence_provenance(chart, payload):
        return None
    if chart.birth_time_confidence != "exact":
        # S03 sampled sign/aspect stability does not prove cross-chart longitude/aspect stability.
        return {}
    raw = payload.get("planet_positions")
    if not isinstance(raw, list):
        return None
    canonical: dict[str, float] = {}
    for value in raw:
        if not isinstance(value, dict):
            return None
        body_value = value.get("body")
        longitude_value = value.get("longitude")
        if not isinstance(body_value, str):
            return None
        body = _body(body_value)
        if chart.birth_time_confidence == "unknown" and body == "moon":
            continue
        try:
            longitude = _longitude(longitude_value)
        except ValueError:
            return None
        existing = canonical.get(body)
        if existing is not None and existing != longitude:
            raise ValueError("conflicting duplicate child position")
        canonical[body] = longitude
    return canonical


def _canonical_parent_houses(houses: Sequence[NatalHouse], *, chart_id: UUID) -> tuple[float, ...] | None:
    if len(houses) != 12:
        return None
    canonical: dict[int, float] = {}
    for row in houses:
        if row.chart_id != chart_id or not 1 <= row.house_number <= 12:
            raise ValueError("parent house references invalid chart lineage")
        longitude = _longitude(row.longitude)
        existing = canonical.get(row.house_number)
        if existing is not None and existing != longitude:
            raise ValueError("conflicting duplicate parent house")
        canonical[row.house_number] = longitude
    if set(canonical) != set(range(1, 13)):
        return None
    cusps = tuple(canonical[number] for number in range(1, 13))
    return cusps if _valid_cusp_cycle(cusps) else None


def _canonical_child_houses(chart: ChildChartVersion) -> tuple[float, ...] | None:
    raw = chart.calculation_payload.get("houses")
    if not isinstance(raw, list) or len(raw) != 12:
        return None
    canonical: dict[int, float] = {}
    for item in raw:
        if not isinstance(item, dict):
            return None
        number = item.get("house_number")
        if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= 12:
            return None
        try:
            longitude = _longitude(item.get("longitude"))
        except ValueError:
            return None
        existing = canonical.get(number)
        if existing is not None and existing != longitude:
            raise ValueError("conflicting duplicate child house")
        canonical[number] = longitude
    if set(canonical) != set(range(1, 13)):
        return None
    cusps = tuple(canonical[number] for number in range(1, 13))
    return cusps if _valid_cusp_cycle(cusps) else None


def _valid_cusp_cycle(cusps: tuple[float, ...]) -> bool:
    if len(cusps) != 12 or len(set(cusps)) != 12:
        return False
    advances = tuple((cusps[(index + 1) % 12] - cusp) % 360.0 for index, cusp in enumerate(cusps))
    return all(0.0 < advance < 360.0 for advance in advances) and abs(sum(advances) - 360.0) <= 1e-9


def _house_for_longitude(longitude: float, cusps: tuple[float, ...]) -> int:
    for index, start in enumerate(cusps):
        end = cusps[(index + 1) % 12]
        if start < end and start <= longitude < end:
            return index + 1
        if start >= end and (longitude >= start or longitude < end):
            return index + 1
    raise ValueError("house cusps do not cover longitude")


def _rule_for_pair(parent_body: str, child_body: str) -> SynastryRule | None:
    for rule in SYNASTRY_RULES:
        if (rule.parent_body, rule.child_body) == (parent_body, child_body):
            return rule
    if parent_body == "saturn" and child_body in PERSONAL_BODIES:
        return SynastryRule(
            parent_body,
            child_body,
            SATURN_DIMENSIONS,
            "pair:saturn-pressure",
            0.08,
            "structure_expectations_pressure_awareness",
            True,
        )
    if child_body == "saturn" and parent_body in PERSONAL_BODIES:
        return SynastryRule(
            parent_body,
            child_body,
            SATURN_DIMENSIONS,
            "pair:saturn-pressure",
            0.08,
            "structure_expectations_pressure_awareness",
            True,
        )
    if parent_body == "jupiter" and child_body in PERSONAL_BODIES:
        return SynastryRule(
            parent_body,
            child_body,
            JUPITER_DIMENSIONS,
            f"pair:jupiter-{child_body}",
            0.08,
            "encouragement_learning_context",
        )
    if child_body == "jupiter" and parent_body in PERSONAL_BODIES:
        return SynastryRule(
            parent_body,
            child_body,
            JUPITER_DIMENSIONS,
            f"pair:{parent_body}-jupiter",
            0.08,
            "encouragement_learning_context",
        )
    return None


def _resolve_aspect(parent_longitude: float, child_longitude: float) -> tuple[Any, float] | None:
    separation = abs(parent_longitude - child_longitude) % 360.0
    separation = min(separation, 360.0 - separation)
    matches = [
        (definition, abs(separation - definition.angle))
        for definition in ASPECT_CATALOG
        if abs(separation - definition.angle) <= definition.orb
    ]
    if not matches:
        return None
    return min(matches, key=lambda item: (item[1], item[0].orb, item[0].code))


def _body(value: str) -> str:
    body = " ".join(value.strip().casefold().split())
    if not body:
        raise ValueError("body must be non-empty")
    return body


def _longitude(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("longitude must be finite and within [0, 360)")
    numeric = float(value)
    if not isfinite(numeric) or not 0.0 <= numeric < 360.0:
        raise ValueError("longitude must be finite and within [0, 360)")
    return numeric
