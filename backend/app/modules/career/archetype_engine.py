"""Deterministic matching of Career dimensions to professional archetypes."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.modules.career.dimension_engine import CareerDimensionResult
from app.modules.career.models import CareerArchetypeScore
from app.modules.career.profile_resolver import CareerProfileResolution
from app.modules.career.schemas import CareerDimensionKey

ARCHETYPE_SCORING_VERSION = "career-archetypes-2"


@dataclass(frozen=True)
class ArchetypeDefinition:
    key: str
    weights: dict[CareerDimensionKey, float]
    preference_boosts: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ArchetypeMatch:
    key: str
    score: float
    confidence: float
    scoring_version: str
    evidence: tuple[str, ...]
    limitations: tuple[str, ...]


ARCHETYPE_CATALOG: tuple[ArchetypeDefinition, ...] = (
    ArchetypeDefinition(
        "architect",
        {
            CareerDimensionKey.SYSTEMS_THINKING: 0.35,
            CareerDimensionKey.ANALYTICAL_THINKING: 0.25,
            CareerDimensionKey.AUTONOMY: 0.20,
            CareerDimensionKey.STRUCTURE: 0.20,
        },
    ),
    ArchetypeDefinition(
        "strategist",
        {
            CareerDimensionKey.SYSTEMS_THINKING: 0.30,
            CareerDimensionKey.LEADERSHIP: 0.25,
            CareerDimensionKey.LONG_TERM_FOCUS: 0.25,
            CareerDimensionKey.AUTONOMY: 0.20,
        },
    ),
    ArchetypeDefinition(
        "specialist",
        {
            CareerDimensionKey.ANALYTICAL_THINKING: 0.35,
            CareerDimensionKey.SYSTEMS_THINKING: 0.25,
            CareerDimensionKey.EXECUTION: 0.20,
            CareerDimensionKey.AUTONOMY: 0.20,
        },
    ),
    ArchetypeDefinition(
        "leader",
        {
            CareerDimensionKey.LEADERSHIP: 0.35,
            CareerDimensionKey.PEOPLE_ORIENTATION: 0.30,
            CareerDimensionKey.COMMUNICATION: 0.20,
            CareerDimensionKey.EXECUTION: 0.15,
        },
    ),
    ArchetypeDefinition(
        "coordinator",
        {
            CareerDimensionKey.PEOPLE_ORIENTATION: 0.30,
            CareerDimensionKey.COMMUNICATION: 0.30,
            CareerDimensionKey.STRUCTURE: 0.20,
            CareerDimensionKey.EXECUTION: 0.20,
        },
    ),
    ArchetypeDefinition(
        "analyst",
        {
            CareerDimensionKey.ANALYTICAL_THINKING: 0.45,
            CareerDimensionKey.SYSTEMS_THINKING: 0.25,
            CareerDimensionKey.STRUCTURE: 0.20,
            CareerDimensionKey.EXECUTION: 0.10,
        },
    ),
    ArchetypeDefinition(
        "builder",
        {
            CareerDimensionKey.EXECUTION: 0.35,
            CareerDimensionKey.STRUCTURE: 0.25,
            CareerDimensionKey.AUTONOMY: 0.20,
            CareerDimensionKey.CREATIVITY: 0.20,
        },
    ),
    ArchetypeDefinition(
        "creator",
        {
            CareerDimensionKey.CREATIVITY: 0.45,
            CareerDimensionKey.INNOVATION: 0.25,
            CareerDimensionKey.AUTONOMY: 0.20,
            CareerDimensionKey.COMMUNICATION: 0.10,
        },
    ),
    ArchetypeDefinition(
        "communicator",
        {
            CareerDimensionKey.COMMUNICATION: 0.45,
            CareerDimensionKey.PEOPLE_ORIENTATION: 0.30,
            CareerDimensionKey.CREATIVITY: 0.15,
            CareerDimensionKey.LEADERSHIP: 0.10,
        },
    ),
    ArchetypeDefinition(
        "researcher",
        {
            CareerDimensionKey.ANALYTICAL_THINKING: 0.35,
            CareerDimensionKey.SYSTEMS_THINKING: 0.30,
            CareerDimensionKey.LONG_TERM_FOCUS: 0.20,
            CareerDimensionKey.INNOVATION: 0.15,
        },
    ),
    ArchetypeDefinition(
        "maker",
        {
            CareerDimensionKey.EXECUTION: 0.35,
            CareerDimensionKey.CREATIVITY: 0.3,
            CareerDimensionKey.STRUCTURE: 0.2,
            CareerDimensionKey.AUTONOMY: 0.15,
        },
        {"hands_on:hands_on": 14, "work_mode:practical": 8, "production_mode:one_off": 5},
    ),
    ArchetypeDefinition(
        "performer",
        {
            CareerDimensionKey.CREATIVITY: 0.35,
            CareerDimensionKey.COMMUNICATION: 0.3,
            CareerDimensionKey.PEOPLE_ORIENTATION: 0.2,
            CareerDimensionKey.EXECUTION: 0.15,
        },
        {"audience:stage": 16, "audience:audience": 8},
    ),
    ArchetypeDefinition(
        "practitioner",
        {
            CareerDimensionKey.EXECUTION: 0.4,
            CareerDimensionKey.ANALYTICAL_THINKING: 0.2,
            CareerDimensionKey.STRUCTURE: 0.2,
            CareerDimensionKey.AUTONOMY: 0.2,
        },
        {"work_mode:practical": 10, "hands_on:hands_on": 10, "service_focus:system": 4},
    ),
    ArchetypeDefinition(
        "caregiver_service",
        {
            CareerDimensionKey.PEOPLE_ORIENTATION: 0.4,
            CareerDimensionKey.COMMUNICATION: 0.25,
            CareerDimensionKey.EXECUTION: 0.2,
            CareerDimensionKey.STRUCTURE: 0.15,
        },
        {"service_focus:client": 14, "work_mode:practical": 5},
    ),
)


def match_archetypes(
    *,
    dimensions: list[CareerDimensionResult],
    resolution: CareerProfileResolution,
) -> tuple[ArchetypeMatch, ...]:
    """Return ranked Top-3 models; no single mandatory type is assigned."""
    by_dimension = {item.dimension: item for item in dimensions}
    matches = [_match_one(definition, by_dimension, resolution) for definition in ARCHETYPE_CATALOG]
    return tuple(sorted(matches, key=lambda item: (-item.score, item.key))[:3])


def _match_one(
    definition: ArchetypeDefinition,
    dimensions: dict[CareerDimensionKey, CareerDimensionResult],
    resolution: CareerProfileResolution,
) -> ArchetypeMatch:
    score = 0.0
    confidence = 0.0
    evidence: list[str] = []
    limitations: list[str] = []
    for key, weight in definition.weights.items():
        result = dimensions.get(key)
        if result is None:
            score += 50.0 * weight
            limitations.append(f"missing:{key.value}")
            continue
        score += result.score * weight
        confidence += result.confidence * weight
        evidence.append(key.value)

    preferences = set(resolution.preferences)
    for preference, boost in definition.preference_boosts.items():
        if preference in preferences:
            score += boost
    if definition.key == "leader" and "manager" in preferences:
        score += 10
    if definition.key == "specialist" and "expert" in preferences:
        score += 12
    if definition.key == "architect" and "expert" in preferences:
        score += 8
    if definition.key == "architect" and "expert_leadership" in preferences:
        score += 5
    if definition.key == "strategist" and "expert_leadership" in preferences:
        score += 14
    if definition.key == "leader" and any(
        item.code == "leadership_without_people_management" for item in resolution.contradictions
    ):
        score -= 20
        limitations.append("preference:low_people_management")

    return ArchetypeMatch(
        key=definition.key,
        score=round(max(0.0, min(100.0, score)), 2),
        confidence=round(max(0.0, min(1.0, confidence)), 4),
        scoring_version=ARCHETYPE_SCORING_VERSION,
        evidence=tuple(sorted(evidence)),
        limitations=tuple(sorted(limitations)),
    )


def build_archetype_rows(
    *,
    career_profile_id: UUID,
    chart_id: UUID,
    generation_id: UUID,
    results: tuple[ArchetypeMatch, ...],
) -> list[CareerArchetypeScore]:
    return [
        CareerArchetypeScore(
            career_profile_id=career_profile_id,
            chart_id=chart_id,
            generation_id=generation_id,
            archetype_key=result.key,
            score=result.score,
            confidence=result.confidence,
            reference_version=result.scoring_version,
            evidence_refs=list(result.evidence),
        )
        for result in results
    ]
