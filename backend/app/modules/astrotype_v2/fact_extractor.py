"""Deterministic fact extraction helpers for Astrotype v2 natal charts."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from app.modules.astrotype_v2 import models
from app.modules.astrotype_v2.reference_data import canonicalize_body_pair
from app.modules.astrotype_v2.reference_lookup import SupportsReferenceLookupRepository, resolve_aspect_interpretation


def build_placement_fact_rows(
    *,
    chart_id: uuid.UUID,
    positions: Sequence[models.NatalPlanetPosition],
    source_version: str = "v2.0",
) -> tuple[list[models.NatalFact], list[models.NatalFactEvidence]]:
    """Build placement facts and evidence rows from normalized v2 planet positions."""
    facts: list[models.NatalFact] = []
    evidence_rows: list[models.NatalFactEvidence] = []

    for position in positions:
        fact_id = uuid.uuid4()
        fact_key = _placement_fact_key(position)
        fact = models.NatalFact(
            id=fact_id,
            chart_id=chart_id,
            fact_type="placement",
            fact_key=fact_key,
            title=_placement_title(position),
            summary=_placement_summary(position),
            weight=1.0,
            confidence=1.0,
            polarity=None,
            section_hint="placements",
            payload={
                "body": position.body,
                "sign": position.sign,
                "sign_degree": position.sign_degree,
                "house_number": position.house_number,
                "retrograde": position.retrograde,
                "longitude": position.longitude,
            },
            source_version=source_version,
        )
        facts.append(fact)
        evidence_rows.append(
            models.NatalFactEvidence(
                fact_id=fact_id,
                chart_id=chart_id,
                source_table=models.NatalPlanetPosition.__tablename__,
                source_id=position.id,
                source_key=f"planet_position:{position.body}",
                payload={"body": position.body, "fact_key": fact_key},
            )
        )

    return facts, evidence_rows


def _placement_fact_key(position: models.NatalPlanetPosition) -> str:
    house_key = f"house_{position.house_number}" if position.house_number is not None else "no_house"
    return f"placement:{_slug(position.body)}:{_slug(position.sign)}:{house_key}"


def build_balance_pattern_fact_rows(
    *,
    chart_id: uuid.UUID,
    balances: Sequence[models.NatalChartBalance],
    patterns: Sequence[models.NatalChartPattern],
    source_version: str = "v2.0",
) -> tuple[list[models.NatalFact], list[models.NatalFactEvidence]]:
    """Build balance and pattern facts from deterministic v2 aggregate rows."""
    facts: list[models.NatalFact] = []
    evidence_rows: list[models.NatalFactEvidence] = []

    for balance in balances:
        fact_id = uuid.uuid4()
        fact_key = f"balance:{_slug(balance.category)}:{_slug(balance.key)}"
        fact = models.NatalFact(
            id=fact_id,
            chart_id=chart_id,
            fact_type="balance",
            fact_key=fact_key,
            title=f"{balance.category} balance: {balance.key}",
            summary=_balance_summary(balance),
            weight=balance.value,
            confidence=1.0,
            polarity=None,
            section_hint="balances",
            payload={"category": balance.category, "key": balance.key, "value": balance.value, "rank": balance.rank},
            source_version=source_version,
        )
        facts.append(fact)
        evidence_rows.append(
            models.NatalFactEvidence(
                fact_id=fact_id,
                chart_id=chart_id,
                source_table=models.NatalChartBalance.__tablename__,
                source_id=balance.id,
                source_key=f"balance:{balance.category}:{balance.key}",
                payload={"fact_key": fact_key},
            )
        )

    for pattern in patterns:
        fact_id = uuid.uuid4()
        fact_key = f"pattern:{_slug(pattern.pattern_code)}"
        fact = models.NatalFact(
            id=fact_id,
            chart_id=chart_id,
            fact_type="pattern",
            fact_key=fact_key,
            title=pattern.label,
            summary=f"Detected pattern: {pattern.label}.",
            weight=pattern.weight or 0.0,
            confidence=1.0,
            polarity=None,
            section_hint="patterns",
            payload={
                "pattern_code": pattern.pattern_code,
                "label": pattern.label,
                "weight": pattern.weight,
                "evidence": pattern.evidence,
            },
            source_version=source_version,
        )
        facts.append(fact)
        evidence_rows.append(
            models.NatalFactEvidence(
                fact_id=fact_id,
                chart_id=chart_id,
                source_table=models.NatalChartPattern.__tablename__,
                source_id=pattern.id,
                source_key=f"pattern:{pattern.pattern_code}",
                payload={"fact_key": fact_key},
            )
        )

    return facts, evidence_rows


def _balance_summary(balance: models.NatalChartBalance) -> str:
    rank_fragment = f"the #{balance.rank} " if balance.rank is not None else "a "
    return f"{balance.key} is {rank_fragment}{balance.category} balance at {balance.value}."


def _placement_title(position: models.NatalPlanetPosition) -> str:
    if position.house_number is None:
        return f"{position.body} in {position.sign}"
    return f"{position.body} in {position.sign}, house {position.house_number}"


def _placement_summary(position: models.NatalPlanetPosition) -> str:
    if position.house_number is None:
        return f"{position.body} is in {position.sign}."
    return f"{position.body} is in {position.sign} in house {position.house_number}."


async def build_aspect_fact_rows(
    repository: SupportsReferenceLookupRepository,
    *,
    chart_id: uuid.UUID,
    aspects: Sequence[models.NatalAspect],
    locale: str = "ru",
    source_version: str = "v2.0",
) -> tuple[list[models.NatalFact], list[models.NatalFactEvidence]]:
    """Build aspect facts and evidence rows from normalized v2 aspects."""
    facts: list[models.NatalFact] = []
    evidence_rows: list[models.NatalFactEvidence] = []

    for aspect in aspects:
        fact_id = uuid.uuid4()
        body_a, body_b = canonicalize_body_pair(aspect.body_a, aspect.body_b)
        interpretation = await resolve_aspect_interpretation(
            repository,
            aspect_code=aspect.aspect_code,
            body_a=body_a,
            body_b=body_b,
            locale=locale,
            source_version=source_version,
        )
        fact_key = _aspect_fact_key(body_a, body_b, aspect.aspect_code)
        reference_payload = _aspect_reference_payload(interpretation)
        fact = models.NatalFact(
            id=fact_id,
            chart_id=chart_id,
            fact_type="aspect",
            fact_key=fact_key,
            title=_aspect_title(body_a, body_b, aspect.aspect_code),
            summary=interpretation.summary if interpretation is not None else _aspect_summary(body_a, body_b, aspect),
            weight=aspect.strength or 0.0,
            confidence=1.0 if interpretation is not None else 0.7,
            polarity=None,
            section_hint="aspects",
            payload={
                "body_a": body_a,
                "body_b": body_b,
                "aspect_code": aspect.aspect_code,
                "angle_degrees": aspect.angle_degrees,
                "orb_degrees": aspect.orb_degrees,
                "applying": aspect.applying,
                "strength": aspect.strength,
                "reference": reference_payload,
            },
            source_version=source_version,
        )
        facts.append(fact)
        evidence_rows.append(
            models.NatalFactEvidence(
                fact_id=fact_id,
                chart_id=chart_id,
                source_table=models.NatalAspect.__tablename__,
                source_id=aspect.id,
                source_key=f"aspect:{body_a}:{body_b}:{aspect.aspect_code}",
                payload={
                    "fact_key": fact_key,
                    "reference_id": str(interpretation.id) if interpretation is not None else None,
                },
            )
        )

    return facts, evidence_rows


def _aspect_fact_key(body_a: str, body_b: str, aspect_code: str) -> str:
    return f"aspect:{_slug(body_a)}:{_slug(body_b)}:{_slug(aspect_code)}"


def _aspect_title(body_a: str, body_b: str, aspect_code: str) -> str:
    return f"{body_a} {aspect_code} {body_b}"


def _aspect_summary(body_a: str, body_b: str, aspect: models.NatalAspect) -> str:
    return f"{body_a} {aspect.aspect_code} {body_b} with orb {aspect.orb_degrees}°."


def _aspect_reference_payload(interpretation: models.AspectPairInterpretation | None) -> dict[str, object] | None:
    if interpretation is None:
        return None
    return {
        "id": str(interpretation.id),
        "summary": interpretation.summary,
        "keywords": interpretation.keywords,
        "source_version": interpretation.source_version,
    }


def _slug(value: str) -> str:
    return value.strip().lower().replace(" ", "_")
