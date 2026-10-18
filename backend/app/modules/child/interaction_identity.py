"""Shared deterministic identities for S07 interaction artifacts."""

from __future__ import annotations

import uuid
from uuid import UUID

INTERACTION_FACT_NAMESPACE = uuid.UUID("04785822-ed8b-505f-8051-c8ce978a437e")
INTERACTION_ROW_NAMESPACE = uuid.UUID("d156b116-30af-5c5b-a911-0c91bd91f230")
INTERACTION_FAMILY_NAMESPACE = uuid.UUID("58851186-cb43-5d50-a292-a37030e77365")
SYNASTRY_ROW_NAMESPACE = uuid.UUID("c1a63410-a183-5b65-922e-e97ddc56e31c")


def pair_identity(
    *,
    child_profile_id: UUID,
    generation_id: UUID,
    parent_chart_id: UUID,
    child_chart_version_id: UUID,
) -> str:
    return f"{child_profile_id}:{generation_id}:{parent_chart_id}:{child_chart_version_id}"


def interaction_fact_id(
    *,
    child_profile_id: UUID,
    generation_id: UUID,
    parent_chart_id: UUID,
    child_chart_version_id: UUID,
    factor_key: str,
    dimension: str,
) -> UUID:
    pair = pair_identity(
        child_profile_id=child_profile_id,
        generation_id=generation_id,
        parent_chart_id=parent_chart_id,
        child_chart_version_id=child_chart_version_id,
    )
    return uuid.uuid5(INTERACTION_FACT_NAMESPACE, f"{pair}:{factor_key}:{dimension}")


def interaction_score_id(
    *,
    child_profile_id: UUID,
    generation_id: UUID,
    parent_chart_id: UUID,
    child_chart_version_id: UUID,
    scoring_version: str,
    dimension: str,
) -> UUID:
    pair = pair_identity(
        child_profile_id=child_profile_id,
        generation_id=generation_id,
        parent_chart_id=parent_chart_id,
        child_chart_version_id=child_chart_version_id,
    )
    return uuid.uuid5(INTERACTION_ROW_NAMESPACE, f"{pair}:{scoring_version}:{dimension}")


def interaction_family_id(lineage_refs: list[str] | tuple[str, ...]) -> UUID:
    return uuid.uuid5(INTERACTION_FAMILY_NAMESPACE, "|".join(sorted(lineage_refs)))


def synastry_evidence_id(
    *,
    child_profile_id: UUID,
    generation_id: UUID,
    parent_chart_id: UUID,
    child_chart_version_id: UUID,
    reference_version: str,
    source_key: str,
) -> UUID:
    pair = pair_identity(
        child_profile_id=child_profile_id,
        generation_id=generation_id,
        parent_chart_id=parent_chart_id,
        child_chart_version_id=child_chart_version_id,
    )
    return uuid.uuid5(SYNASTRY_ROW_NAMESPACE, f"{pair}:{reference_version}:{source_key}")
