"""Serializable fact/evidence payload builders for Astrotype v2."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.modules.astrotype_v2 import models


def build_fact_evidence_payload(
    *,
    facts: Sequence[models.NatalFact],
    evidence: Sequence[models.NatalFactEvidence],
) -> list[dict[str, Any]]:
    """Return deterministic API-ready facts with grouped v2 evidence rows."""
    evidence_by_fact_id: dict[object, list[models.NatalFactEvidence]] = {}
    for evidence_row in evidence:
        if not evidence_row.source_table.startswith("astrotype_v2_"):
            raise ValueError(f"non-v2 evidence source: {evidence_row.source_table}")
        evidence_by_fact_id.setdefault(evidence_row.fact_id, []).append(evidence_row)

    return [_fact_payload(fact, evidence_by_fact_id.get(fact.id, [])) for fact in facts]


def _fact_payload(fact: models.NatalFact, evidence_rows: Sequence[models.NatalFactEvidence]) -> dict[str, Any]:
    return {
        "id": str(fact.id),
        "chart_id": str(fact.chart_id),
        "fact_type": fact.fact_type,
        "fact_key": fact.fact_key,
        "title": fact.title,
        "summary": fact.summary,
        "weight": fact.weight,
        "confidence": fact.confidence,
        "polarity": fact.polarity,
        "section_hint": fact.section_hint,
        "payload": fact.payload,
        "source_version": fact.source_version,
        "evidence": [_evidence_payload(evidence_row) for evidence_row in evidence_rows],
    }


def _evidence_payload(evidence_row: models.NatalFactEvidence) -> dict[str, Any]:
    return {
        "id": str(evidence_row.id),
        "source_table": evidence_row.source_table,
        "source_id": str(evidence_row.source_id) if evidence_row.source_id is not None else None,
        "source_key": evidence_row.source_key,
        "payload": evidence_row.payload,
    }
