"""Bounded deterministic Guidance Facts for Child Report S09."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final, cast
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.child import models
from app.modules.child.age_resolver import AgeStage
from app.modules.child.context_resolver import (
    MIN_SCORE_CONFIDENCE,
    RESOLVER_VERSION,
    ContextResolution,
    ResolutionEntry,
    ResolverAgeSnapshot,
)
from app.modules.child.questionnaire_persistence import ChildContextResolutionRepository
from app.modules.child.repository import ChildLineageMismatchError, ChildRepository
from app.modules.child.scoring.types import InteractionDimension

GUIDANCE_FACTS_CONTRACT_VERSION: Final = "child-guidance-facts-v1"
GUIDANCE_FACTS_CONTRACT_V2: Final = "child-guidance-facts-v2"
GUIDANCE_FACTS_CONTRACT_V3: Final = "child-guidance-facts-v3"
CURRENT_GUIDANCE_FACTS_CONTRACT_VERSION: Final = GUIDANCE_FACTS_CONTRACT_V3
SOURCE_PROFILE_CONTRACT_VERSIONS: Final = (GUIDANCE_FACTS_CONTRACT_V2, GUIDANCE_FACTS_CONTRACT_V3)
SUPPORTED_GUIDANCE_FACTS_CONTRACT_VERSIONS: Final = (GUIDANCE_FACTS_CONTRACT_VERSION, *SOURCE_PROFILE_CONTRACT_VERSIONS)
LOW_CONFIDENCE_THRESHOLD: Final = 0.5
_STRONG_MATCH_THRESHOLD: Final = 65.0
_FRICTION_THRESHOLD: Final = 35.0

_AVOID_PATTERN_BY_DIMENSION: Final[dict[str, str]] = {
    "emotional_attunement": "dismiss_child_signals",
    "boundary_fit": "escalate_pressure_during_boundary_protest",
    "soothing_compatibility": "repeat_soothing_that_increases_distress",
    "communication_fit": "overload_with_explanations_during_conflict",
    "autonomy_balance": "interpret_independence_as_disobedience",
    "learning_interaction": "correct_before_checking_understanding",
    "conflict_pattern": "mirror_child_escalation",
    "tempo_fit": "expect_behavior_above_current_age_stage",
}
GUIDANCE_AVOID_PATTERN_CODES: Final = frozenset({*_AVOID_PATTERN_BY_DIMENSION.values(), "escalate_without_observation"})


@dataclass(frozen=True, slots=True)
class GuidanceInteractionScore:
    dimension: str
    score: float
    confidence: float
    pattern: str
    scoring_version: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GuidanceProfileScore:
    source_kind: str
    dimension: str
    score: float
    confidence: float
    scoring_version: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChildGuidanceFacts:
    contract_version: str
    parent_profile_id: UUID
    child_id: UUID
    generation_id: UUID
    core_report_version: int
    age_snapshot_id: UUID
    age_stage: AgeStage
    strong_matches: tuple[Mapping[str, Any], ...]
    friction_points: tuple[Mapping[str, Any], ...]
    parent_strengths: tuple[Mapping[str, Any], ...]
    compensation_areas: tuple[Mapping[str, Any], ...]
    recommended_actions: tuple[Mapping[str, Any], ...]
    avoid_patterns: tuple[Mapping[str, Any], ...]
    confidence_markers: tuple[Mapping[str, Any], ...]
    evidence_registry: Mapping[str, Mapping[str, Any]]
    input_hash: str
    source_profiles: tuple[Mapping[str, Any], ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return {
            **(
                {"source_profiles": _thaw(self.source_profiles)}
                if self.contract_version in SOURCE_PROFILE_CONTRACT_VERSIONS
                else {}
            ),
            "contract_version": self.contract_version,
            "parent_profile_id": str(self.parent_profile_id),
            "child_id": str(self.child_id),
            "core_report_version": self.core_report_version,
            "age_snapshot_id": str(self.age_snapshot_id),
            "strong_matches": _thaw(self.strong_matches),
            "friction_points": _thaw(self.friction_points),
            "parent_strengths": _thaw(self.parent_strengths),
            "compensation_areas": _thaw(self.compensation_areas),
            "recommended_actions": _thaw(self.recommended_actions),
            "avoid_patterns": _thaw(self.avoid_patterns),
            "confidence_markers": _thaw(self.confidence_markers),
            "evidence_registry": _thaw(self.evidence_registry),
        }


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({str(key): _freeze(nested) for key, nested in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze(nested) for nested in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return [_thaw(nested) for nested in value]
    return value


def _entry_fact(entry: ResolutionEntry, *, prefix: str) -> dict[str, Any]:
    return {
        "id": f"{prefix}:{entry.id}",
        "topic": entry.topic,
        "dimension": entry.dimension,
        "confidence": entry.confidence,
        "reason_code": entry.reason_code,
        "action_code": entry.action_code,
        "evidence_refs": list(entry.source_refs),
    }


def _action_fact(entry: ResolutionEntry, *, fallback_evidence_ref: str) -> dict[str, Any]:
    return {
        "id": f"action:{entry.id}",
        "topic": entry.topic,
        "dimension": entry.dimension,
        "applicability": entry.applicability,
        "action_code": entry.action_code,
        "reason_code": entry.reason_code,
        "target": "caregiver",
        "confidence": entry.confidence,
        "evidence_refs": list(entry.source_refs or (fallback_evidence_ref,)),
    }


def _score_fact(score: GuidanceInteractionScore, *, prefix: str) -> dict[str, Any]:
    return {
        "id": f"{prefix}:{score.dimension}",
        "dimension": score.dimension,
        "score": score.score,
        "confidence": score.confidence,
        "pattern": score.pattern,
        "evidence_refs": list(score.evidence_refs),
    }


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_guidance_facts(
    *,
    parent_profile_id: UUID,
    child_id: UUID,
    generation_id: UUID,
    core_report_version: int,
    age_snapshot: ResolverAgeSnapshot,
    resolution: ContextResolution,
    interaction_scores: tuple[GuidanceInteractionScore, ...],
    profile_scores: tuple[GuidanceProfileScore, ...] = (),
    contract_version: str = GUIDANCE_FACTS_CONTRACT_VERSION,
) -> ChildGuidanceFacts:
    """Build the only bounded content contract allowed into Child Report prompts."""

    context_reference = f"context_resolution:{resolution.input_hash}"
    if contract_version not in SUPPORTED_GUIDANCE_FACTS_CONTRACT_VERSIONS:
        raise ValueError("Unsupported Guidance Facts contract")
    if profile_scores and contract_version == GUIDANCE_FACTS_CONTRACT_VERSION:
        raise ValueError("Source profiles require the current content contract")
    if contract_version in SOURCE_PROFILE_CONTRACT_VERSIONS:
        profile_scores = (
            *profile_scores,
            *(
                GuidanceProfileScore(
                    "interaction",
                    score.dimension,
                    score.score,
                    score.confidence,
                    score.scoring_version,
                    score.evidence_refs,
                )
                for score in interaction_scores
            ),
        )
    source_profiles: tuple[dict[str, Any], ...] = tuple(
        {
            "id": f"profile:{score.source_kind}:{score.dimension}",
            "source_kind": score.source_kind,
            "dimension": score.dimension,
            "score": score.score,
            "confidence": score.confidence,
            "scoring_version": score.scoring_version,
            "evidence_refs": list(score.evidence_refs),
        }
        for score in sorted(profile_scores, key=lambda item: (item.source_kind, item.dimension))
    )
    strong_matches = tuple(
        _score_fact(score, prefix="strong_match")
        for score in sorted(interaction_scores, key=lambda item: item.dimension)
        if score.confidence >= MIN_SCORE_CONFIDENCE and score.score >= _STRONG_MATCH_THRESHOLD
    )
    friction_points = tuple(
        _score_fact(score, prefix="friction_point")
        for score in sorted(interaction_scores, key=lambda item: item.dimension)
        if score.confidence >= MIN_SCORE_CONFIDENCE and score.score <= _FRICTION_THRESHOLD
    )
    parent_strengths = (
        tuple(_entry_fact(entry, prefix="parent_strength") for entry in resolution.natural_strengths)
        if contract_version == GUIDANCE_FACTS_CONTRACT_VERSION
        else ()  # v2 parent resources are primary parent-style source profiles, not pair matches.
    )
    compensation_areas = tuple(_entry_fact(entry, prefix="compensation") for entry in resolution.compensation_areas)
    actionable_entries = (
        *resolution.natural_strengths,
        *resolution.potential_friction,
        *resolution.compensation_areas,
        *resolution.age_relevant_guidance,
        *resolution.confirmations,
        *resolution.contradictions,
        *resolution.unresolved_ambiguities,
    )
    recommended_actions = tuple(
        _action_fact(entry, fallback_evidence_ref=context_reference) for entry in actionable_entries
    )
    avoid_patterns = tuple(
        {
            "id": f"avoid:{entry.id}",
            "dimension": entry.dimension,
            "pattern_code": _AVOID_PATTERN_BY_DIMENSION.get(entry.dimension or "", "escalate_without_observation"),
            "target": "caregiver",
            "confidence": entry.confidence,
            "evidence_refs": list(entry.source_refs),
        }
        for entry in resolution.potential_friction
    )
    serialized_facts = (
        *source_profiles,
        *strong_matches,
        *friction_points,
        *parent_strengths,
        *compensation_areas,
        *recommended_actions,
        *avoid_patterns,
    )
    confidence_markers = tuple(
        {
            "fact_id": fact["id"],
            "level": "low",
            "required_language": "conditional",
        }
        for fact in serialized_facts
        if float(fact["confidence"]) < LOW_CONFIDENCE_THRESHOLD
    )

    evidence_registry: dict[str, dict[str, Any]] = {
        f"age_snapshot:{age_snapshot.id}": {
            "source_type": "age_snapshot",
            "source_id": str(age_snapshot.id),
            "age_stage": age_snapshot.age_stage,
            "rules_version": age_snapshot.age_rules_version,
            "resolver_entry_ids": [],
            "reason_codes": [],
        },
        context_reference: {
            "source_type": "context_resolution",
            "resolver_version": resolution.resolver_version,
            "input_hash": resolution.input_hash,
            "resolver_entry_ids": [],
            "reason_codes": [],
        },
    }
    for score in sorted(interaction_scores, key=lambda item: item.dimension):
        for reference in score.evidence_refs:
            evidence_registry[reference] = {
                "source_type": "interaction_score",
                "dimension": score.dimension,
                "score": score.score,
                "pattern": score.pattern,
                "scoring_version": score.scoring_version,
                "confidence": score.confidence,
                "resolver_entry_ids": [],
                "reason_codes": [],
            }
    for fact in source_profiles:
        if fact["source_kind"] == "interaction":
            continue  # The original authoritative interaction registry entry owns this score.
        for reference in fact["evidence_refs"]:
            if reference in evidence_registry:
                raise ValueError("Source profile evidence must have unique semantic ownership")
            evidence_registry[reference] = {
                "source_type": "source_profile",
                **{key: fact[key] for key in ("source_kind", "dimension", "score", "confidence", "scoring_version")},
            }
    for entry in resolution.all_entries():
        for reference in entry.source_refs or (context_reference,):
            metadata = evidence_registry.setdefault(
                reference,
                {
                    "source_type": reference.split(":", 1)[0],
                    "resolver_entry_ids": [],
                    "reason_codes": [],
                },
            )
            resolver_entry_ids = cast(list[str], metadata.setdefault("resolver_entry_ids", []))
            reason_codes = cast(list[str], metadata.setdefault("reason_codes", []))
            if entry.id not in resolver_entry_ids:
                resolver_entry_ids.append(entry.id)
            if entry.reason_code not in reason_codes:
                reason_codes.append(entry.reason_code)
            resolver_entry_ids.sort()
            reason_codes.sort()

    unhashed_payload: dict[str, Any] = {
        **({"source_profiles": list(source_profiles)} if contract_version in SOURCE_PROFILE_CONTRACT_VERSIONS else {}),
        "contract_version": contract_version,
        "parent_profile_id": str(parent_profile_id),
        "child_id": str(child_id),
        "core_report_version": core_report_version,
        "age_snapshot_id": str(age_snapshot.id),
        "strong_matches": list(strong_matches),
        "friction_points": list(friction_points),
        "parent_strengths": list(parent_strengths),
        "compensation_areas": list(compensation_areas),
        "recommended_actions": list(recommended_actions),
        "avoid_patterns": list(avoid_patterns),
        "confidence_markers": list(confidence_markers),
        "evidence_registry": evidence_registry,
        "source_contract": {
            "resolver_version": resolution.resolver_version,
            "resolver_input_hash": resolution.input_hash,
        },
    }
    input_hash = _canonical_hash(unhashed_payload)
    evidence_registry[f"guidance_contract:{input_hash}"] = {
        "source_type": "guidance_contract",
        "contract_version": contract_version,
        "input_hash": input_hash,
    }
    return ChildGuidanceFacts(
        contract_version=contract_version,
        parent_profile_id=parent_profile_id,
        child_id=child_id,
        generation_id=generation_id,
        core_report_version=core_report_version,
        age_snapshot_id=age_snapshot.id,
        age_stage=age_snapshot.age_stage,
        strong_matches=cast(tuple[Mapping[str, Any], ...], _freeze(strong_matches)),
        friction_points=cast(tuple[Mapping[str, Any], ...], _freeze(friction_points)),
        parent_strengths=cast(tuple[Mapping[str, Any], ...], _freeze(parent_strengths)),
        compensation_areas=cast(tuple[Mapping[str, Any], ...], _freeze(compensation_areas)),
        recommended_actions=cast(tuple[Mapping[str, Any], ...], _freeze(recommended_actions)),
        avoid_patterns=cast(tuple[Mapping[str, Any], ...], _freeze(avoid_patterns)),
        confidence_markers=cast(tuple[Mapping[str, Any], ...], _freeze(confidence_markers)),
        evidence_registry=cast(Mapping[str, Mapping[str, Any]], _freeze(evidence_registry)),
        input_hash=input_hash,
        source_profiles=cast(tuple[Mapping[str, Any], ...], _freeze(source_profiles)),
    )


@dataclass(frozen=True, slots=True)
class GuidanceFactsCreateResult:
    artifact: models.ChildGuidanceFacts
    created: bool


def _resolution_entries(raw: object) -> tuple[ResolutionEntry, ...]:
    if not isinstance(raw, list):
        raise ChildLineageMismatchError("Context Resolution payload is malformed")
    entries: list[ResolutionEntry] = []
    try:
        for item in raw:
            if not isinstance(item, dict):
                raise TypeError
            entries.append(
                ResolutionEntry(
                    id=str(item["id"]),
                    topic=str(item["topic"]),
                    dimension=cast(str | None, item["dimension"]),
                    confidence=float(item["confidence"]),
                    source_refs=tuple(str(reference) for reference in item["source_refs"]),
                    reason_code=str(item["reason_code"]),
                    action_code=str(item["action_code"]),
                    priority=str(item.get("priority", "normal")),
                    applicability=str(item.get("applicability", "general")),
                )
            )
    except (KeyError, TypeError, ValueError) as exc:
        raise ChildLineageMismatchError("Context Resolution payload is malformed") from exc
    return tuple(entries)


class ChildGuidanceFactsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load_domain_facts(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        generation_id: UUID,
        core_report_version: int,
    ) -> ChildGuidanceFacts:
        result = await self.create_or_load(
            owner_user_id=owner_user_id,
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            core_report_version=core_report_version,
        )
        artifact = result.artifact
        payload = artifact.payload
        registry = artifact.evidence_registry
        age_metadata = next(
            (value for value in registry.values() if value.get("source_type") == "age_snapshot"),
            None,
        )
        contract_metadata = next(
            (value for value in registry.values() if value.get("source_type") == "guidance_contract"),
            None,
        )
        if age_metadata is None or contract_metadata is None:
            raise ChildLineageMismatchError("Persisted Guidance Facts metadata is incomplete")
        return ChildGuidanceFacts(
            contract_version=artifact.contract_version,
            parent_profile_id=UUID(str(payload["parent_profile_id"])),
            child_id=UUID(str(payload["child_id"])),
            generation_id=artifact.generation_id,
            core_report_version=artifact.core_report_version,
            age_snapshot_id=artifact.age_snapshot_id,
            age_stage=cast(AgeStage, age_metadata["age_stage"]),
            strong_matches=cast(tuple[Mapping[str, Any], ...], _freeze(payload["strong_matches"])),
            friction_points=cast(tuple[Mapping[str, Any], ...], _freeze(payload["friction_points"])),
            parent_strengths=cast(tuple[Mapping[str, Any], ...], _freeze(payload["parent_strengths"])),
            compensation_areas=cast(tuple[Mapping[str, Any], ...], _freeze(payload["compensation_areas"])),
            recommended_actions=cast(tuple[Mapping[str, Any], ...], _freeze(payload["recommended_actions"])),
            avoid_patterns=cast(tuple[Mapping[str, Any], ...], _freeze(payload["avoid_patterns"])),
            confidence_markers=cast(tuple[Mapping[str, Any], ...], _freeze(payload["confidence_markers"])),
            evidence_registry=cast(Mapping[str, Mapping[str, Any]], _freeze(registry)),
            input_hash=str(contract_metadata["input_hash"]),
            source_profiles=cast(tuple[Mapping[str, Any], ...], _freeze(payload.get("source_profiles", []))),
        )

    async def create_or_load(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        generation_id: UUID,
        core_report_version: int,
    ) -> GuidanceFactsCreateResult:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"child-guidance:{child_profile_id}:{generation_id}"},
        )
        # A generation has one immutable content policy. Repairs require a new
        # full-report generation, never an implicit reinterpretation of v1.
        stored_versions = (
            await self.session.scalars(
                select(models.ChildGuidanceFacts.contract_version).where(
                    models.ChildGuidanceFacts.generation_id == generation_id,
                    models.ChildGuidanceFacts.child_profile_id == child_profile_id,
                )
            )
        ).all()
        if len(stored_versions) > 1:
            raise ChildLineageMismatchError("Guidance Facts version lineage is ambiguous")
        contract_version = stored_versions[0] if stored_versions else CURRENT_GUIDANCE_FACTS_CONTRACT_VERSION
        if contract_version not in SUPPORTED_GUIDANCE_FACTS_CONTRACT_VERSIONS:
            raise ChildLineageMismatchError("Unsupported persisted Guidance Facts version")
        resolution_row = await ChildContextResolutionRepository(self.session).load(
            owner_user_id=owner_user_id,
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            resolver_version=RESOLVER_VERSION,
        )
        child = await self.session.scalar(
            select(models.ChildProfile)
            .where(
                models.ChildProfile.id == child_profile_id,
                models.ChildProfile.owner_user_id == owner_user_id,
            )
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        age = await self.session.scalar(
            select(models.ChildAgeSnapshot)
            .where(
                models.ChildAgeSnapshot.id == resolution_row.age_snapshot_id,
                models.ChildAgeSnapshot.child_profile_id == child_profile_id,
            )
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        interaction_profile = await ChildRepository(self.session).load_interaction_profile(
            owner_user_id=owner_user_id,
            child_profile_id=child_profile_id,
            generation_id=generation_id,
        )
        score_rows = interaction_profile.scores
        expected_dimensions = {dimension.value for dimension in InteractionDimension}
        if child is None or age is None or {row.dimension for row in score_rows} != expected_dimensions:
            raise ChildLineageMismatchError("Guidance Facts source lineage is incomplete")

        resolution = ContextResolution(
            resolver_version=resolution_row.resolver_version,
            input_hash=resolution_row.input_hash,
            natural_strengths=_resolution_entries(resolution_row.natural_strengths),
            potential_friction=_resolution_entries(resolution_row.potential_friction),
            compensation_areas=_resolution_entries(resolution_row.compensation_areas),
            age_relevant_guidance=_resolution_entries(resolution_row.age_relevant_guidance),
            confirmations=_resolution_entries(resolution_row.confirmations),
            contradictions=_resolution_entries(resolution_row.contradictions),
            unresolved_ambiguities=_resolution_entries(resolution_row.unresolved_ambiguities),
        )
        age_snapshot = ResolverAgeSnapshot(
            id=age.id,
            age_stage=cast(AgeStage, age.age_stage),
            as_of_date=age.as_of_date,
            age_rules_version=age.age_rules_version,
        )
        scores = tuple(
            GuidanceInteractionScore(
                dimension=row.dimension,
                score=float(row.score),
                confidence=float(row.confidence),
                pattern=row.pattern,
                scoring_version=row.scoring_version,
                evidence_refs=(f"child_interaction_scores:{row.id}:{row.scoring_version}",),
            )
            for row in score_rows
        )
        profile_scores: list[GuidanceProfileScore] = []
        if contract_version in SOURCE_PROFILE_CONTRACT_VERSIONS:
            repository = ChildRepository(self.session)
            parent = await repository.load_parent_style_profile(
                owner_user_id=owner_user_id,
                child_profile_id=child_profile_id,
                generation_id=generation_id,
            )
            needs = await repository.load_child_need_profile(
                owner_user_id=owner_user_id,
                child_profile_id=child_profile_id,
                generation_id=generation_id,
            )
            for kind, prefix, rows in (
                ("parent_style", "child_parent_style_scores", parent.scores),
                ("child_needs", "child_need_scores", needs.scores),
            ):
                profile_scores.extend(
                    GuidanceProfileScore(
                        source_kind=kind,
                        dimension=row.dimension,
                        score=float(row.score),
                        confidence=float(row.confidence),
                        scoring_version=row.scoring_version,
                        evidence_refs=(f"{prefix}:{row.id}:{row.scoring_version}",),
                    )
                    for row in rows
                )
        facts = build_guidance_facts(
            parent_profile_id=child.parent_profile_id,
            child_id=child_profile_id,
            generation_id=generation_id,
            core_report_version=core_report_version,
            age_snapshot=age_snapshot,
            resolution=resolution,
            interaction_scores=scores,
            profile_scores=tuple(profile_scores),
            contract_version=contract_version,
        )
        from app.modules.child.quality import validate_guidance_facts

        validate_guidance_facts(facts)
        full_payload = facts.to_payload()
        evidence_registry = cast(dict[str, Any], full_payload.pop("evidence_registry"))
        existing = await self.session.scalar(
            select(models.ChildGuidanceFacts)
            .where(
                models.ChildGuidanceFacts.generation_id == generation_id,
                models.ChildGuidanceFacts.contract_version == contract_version,
            )
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        if existing is not None:
            if (
                existing.child_profile_id != child_profile_id
                or existing.age_snapshot_id != age.id
                or existing.core_report_version != core_report_version
                or existing.payload != full_payload
                or existing.evidence_registry != evidence_registry
            ):
                raise ChildLineageMismatchError("Persisted Guidance Facts are corrupt or stale")
            return GuidanceFactsCreateResult(artifact=existing, created=False)

        artifact = models.ChildGuidanceFacts(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            age_snapshot_id=age.id,
            contract_version=contract_version,
            core_report_version=core_report_version,
            payload=full_payload,
            evidence_registry=evidence_registry,
        )
        self.session.add(artifact)
        await self.session.flush()
        return GuidanceFactsCreateResult(artifact=artifact, created=True)
