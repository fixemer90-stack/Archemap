"""Assemble final Astrotype v2 natal reports from validated segment artifacts."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections import Counter
from typing import Any

from app.modules.astrotype_v2 import models
from app.modules.astrotype_v2.schemas import NatalReportSectionV2, NatalReportV2, ReportSegmentOutputV2

REPORT_CONTRACT_VERSION = "natal_report_v2"


class ReportAssemblyError(ValueError):
    """Raised when validated segment artifacts cannot form a complete report."""


def assemble_natal_report_v2(
    *,
    chart_id: uuid.UUID,
    synthesis_row: models.NatalSynthesis,
    outline_row: models.ReportOutline,
    infographic_row: models.NatalInfographicData,
    segment_rows: list[models.ReportSegmentGeneration],
    version: int,
) -> NatalReportV2:
    """Assemble a final report contract without rewriting segment prose."""

    required_section_keys = _required_section_keys(outline_row)
    segments_by_key = _validate_segment_set(segment_rows=segment_rows, required_section_keys=required_section_keys)
    sections = [_section_from_segment(segments_by_key[section_key]) for section_key in required_section_keys]
    _validate_sections(sections=sections, synthesis_row=synthesis_row)
    evidence_index = _build_evidence_index(sections=sections)
    technical_basis = _build_technical_basis(
        synthesis_row=synthesis_row,
        outline_row=outline_row,
        infographic_row=infographic_row,
    )
    deterministic_payload = {
        "synthesis": synthesis_row.payload,
        "outline": outline_row.outline,
        "technical_basis": technical_basis,
    }
    narrative_payload = {
        "sections": [section.model_dump(mode="json") for section in sections],
        "section_order": required_section_keys,
        "evidence_index": evidence_index,
    }
    assembled_payload = {
        "contract_version": REPORT_CONTRACT_VERSION,
        "chart_id": str(chart_id),
        "version": version,
        "status": "complete",
        "input_hashes": _input_hashes(
            synthesis_row=synthesis_row,
            outline_row=outline_row,
            infographic_row=infographic_row,
            segment_rows=[segments_by_key[key] for key in required_section_keys],
        ),
        "version_lineage": {"previous_version": max(version - 1, 0), "version": version},
    }
    return NatalReportV2(
        chart_id=chart_id,
        version=version,
        status="complete",
        narrative_sections=sections,
        evidence_index=evidence_index,
        technical_basis=technical_basis,
        deterministic_payload=deterministic_payload,
        narrative_payload=narrative_payload,
        assembled_payload=assembled_payload,
    )


def build_natal_report_row(
    *,
    chart_id: uuid.UUID,
    synthesis_row: models.NatalSynthesis,
    outline_row: models.ReportOutline,
    infographic_row: models.NatalInfographicData,
    segment_rows: list[models.ReportSegmentGeneration],
    previous_version: int | None = None,
) -> models.NatalReport:
    """Build the next versioned report row without mutating older rows."""

    next_version = (previous_version or 0) + 1
    report = assemble_natal_report_v2(
        chart_id=chart_id,
        synthesis_row=synthesis_row,
        outline_row=outline_row,
        infographic_row=infographic_row,
        segment_rows=segment_rows,
        version=next_version,
    )
    assembled_payload = report.assembled_payload | {
        "version_lineage": {"previous_version": previous_version, "version": next_version}
    }
    return models.NatalReport(
        chart_id=chart_id,
        synthesis_id=getattr(synthesis_row, "id", None),
        outline_id=getattr(outline_row, "id", None),
        infographic_data_id=getattr(infographic_row, "id", None),
        status=report.status,
        version=next_version,
        deterministic_payload=report.deterministic_payload,
        narrative_payload=report.narrative_payload,
        assembled_payload=assembled_payload,
    )


def _required_section_keys(outline_row: models.ReportOutline) -> list[str]:
    if outline_row.section_keys:
        return list(outline_row.section_keys)
    sections = outline_row.outline.get("sections", [])
    keys = [section["id"] for section in sections if "id" in section]
    if not keys:
        raise ReportAssemblyError("missing required sections in outline")
    return keys


def _validate_segment_set(
    *,
    segment_rows: list[models.ReportSegmentGeneration],
    required_section_keys: list[str],
) -> dict[str, models.ReportSegmentGeneration]:
    counts = Counter(segment.section_key for segment in segment_rows)
    duplicates = sorted(section_key for section_key, count in counts.items() if count > 1)
    if duplicates:
        raise ReportAssemblyError(f"duplicate section artifacts: {duplicates}")

    by_key = {segment.section_key: segment for segment in segment_rows}
    missing = sorted(set(required_section_keys) - set(by_key))
    if missing:
        raise ReportAssemblyError(f"missing required sections: {missing}")

    not_ready = sorted(key for key in required_section_keys if by_key[key].status != "ready")
    if not_ready:
        raise ReportAssemblyError(f"segments not ready: {not_ready}")
    return by_key


def _section_from_segment(segment_row: models.ReportSegmentGeneration) -> NatalReportSectionV2:
    response = ReportSegmentOutputV2.model_validate(segment_row.payload.get("response", {}))
    if response.section_id != segment_row.section_key:
        raise ReportAssemblyError("segment response section mismatch")
    return NatalReportSectionV2(
        section_id=response.section_id,
        title=response.title,
        body=response.body,
        covered_theme_ids=list(response.covered_theme_ids),
        evidence_ids=list(response.evidence_ids),
        source_segment_hash=segment_row.payload.get("response_hash"),
    )


def _validate_sections(*, sections: list[NatalReportSectionV2], synthesis_row: models.NatalSynthesis) -> None:
    bodies = [_canonical_text(section.body) for section in sections]
    duplicate_bodies = [body for body, count in Counter(bodies).items() if count > 1]
    if duplicate_bodies:
        raise ReportAssemblyError("duplicate narrative section body")

    known_evidence_ids = _known_evidence_ids(synthesis_row)
    used_evidence_ids = {evidence_id for section in sections for evidence_id in section.evidence_ids}
    missing_evidence_ids = sorted(used_evidence_ids - known_evidence_ids)
    if missing_evidence_ids:
        raise ReportAssemblyError(f"missing evidence in deterministic basis: {missing_evidence_ids}")

    for section in sections:
        if not section.covered_theme_ids:
            raise ReportAssemblyError(f"section {section.section_id} has no covered themes")
        if not section.evidence_ids:
            raise ReportAssemblyError(f"section {section.section_id} has no evidence ids")


def _known_evidence_ids(synthesis_row: models.NatalSynthesis) -> set[str]:
    ids: set[str] = set()
    for theme in synthesis_row.payload.get("dominant_themes", []):
        ids.update(str(evidence_id) for evidence_id in theme.get("evidence_ids", []))
    return ids


def _build_evidence_index(*, sections: list[NatalReportSectionV2]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for section in sections:
        for evidence_id in section.evidence_ids:
            entry = index.setdefault(evidence_id, {"evidence_id": evidence_id, "section_ids": [], "theme_ids": []})
            if section.section_id not in entry["section_ids"]:
                entry["section_ids"].append(section.section_id)
            for theme_id in section.covered_theme_ids:
                if theme_id not in entry["theme_ids"]:
                    entry["theme_ids"].append(theme_id)
    return dict(sorted(index.items()))


def _build_technical_basis(
    *,
    synthesis_row: models.NatalSynthesis,
    outline_row: models.ReportOutline,
    infographic_row: models.NatalInfographicData,
) -> dict[str, Any]:
    return {
        "contract_version": "natal_report_technical_basis_v2",
        "source_version": outline_row.source_version,
        "facts_version": synthesis_row.facts_version,
        "calculation_layer": infographic_row.calculation_layer,
        "synthesis_summary": {
            "input_fact_keys": synthesis_row.payload.get("input_fact_keys", []),
            "dominant_theme_ids": [theme.get("id") for theme in synthesis_row.payload.get("dominant_themes", [])],
        },
        "outline_summary": {
            "section_keys": list(outline_row.section_keys),
            "section_count": len(outline_row.section_keys),
        },
    }


def _input_hashes(
    *,
    synthesis_row: models.NatalSynthesis,
    outline_row: models.ReportOutline,
    infographic_row: models.NatalInfographicData,
    segment_rows: list[models.ReportSegmentGeneration],
) -> dict[str, Any]:
    return {
        "synthesis": _stable_hash(synthesis_row.payload),
        "outline": _stable_hash(outline_row.outline),
        "infographic": _stable_hash(infographic_row.calculation_layer),
        "segments": {
            segment.section_key: segment.payload.get("response_hash") or _stable_hash(segment.payload)
            for segment in segment_rows
        },
    }


def _canonical_text(text: str) -> str:
    return " ".join(text.lower().split())


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
