"""Deterministic assembly of validated Child Report narrative sections."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.modules.child import models
from app.modules.child.guidance_facts import ChildGuidanceFacts
from app.modules.child.narrative import (
    CHILD_PROMPT_VERSION,
    ChildNarrativeValidationError,
    ChildSegmentOutput,
    _error_type_is_valid,
    _model_name_is_valid,
    _provider_name_is_valid,
    _section_fact_id_map,
    _stable_hash,
    build_child_section_inputs,
    validate_segment_output,
)
from app.modules.child.prompts.v1 import SECTION_METADATA, build_child_section_prompt


def _verify_generation_metadata(
    *,
    row: models.ChildSegmentGeneration,
    section_input: Any,
) -> dict[str, str]:
    diagnostics = row.diagnostics
    if not isinstance(diagnostics, Mapping):
        raise ChildNarrativeValidationError("segment diagnostics are invalid")
    provider = diagnostics.get("provider")
    model = diagnostics.get("model")
    if row.prompt_version != CHILD_PROMPT_VERSION or diagnostics.get("prompt_version") != CHILD_PROMPT_VERSION:
        raise ChildNarrativeValidationError("segment prompt version mismatch")
    if not _provider_name_is_valid(provider):
        raise ChildNarrativeValidationError("segment provider metadata is missing")
    if not _model_name_is_valid(model) or model != row.model:
        raise ChildNarrativeValidationError("segment model metadata mismatch")
    if diagnostics.get("retry_scope") != section_input.retry_scope:
        raise ChildNarrativeValidationError("segment retry scope mismatch")
    expected_input_hash = _stable_hash(section_input.model_dump(mode="json"))
    expected_prompt_hash = _stable_hash({"prompt": build_child_section_prompt(section_input)})
    if diagnostics.get("input_hash") != expected_input_hash:
        raise ChildNarrativeValidationError("segment input hash mismatch")
    if diagnostics.get("prompt_hash") != expected_prompt_hash:
        raise ChildNarrativeValidationError("segment prompt hash mismatch")
    return {"provider": provider, "model": model, "prompt_version": row.prompt_version}


def assemble_child_report_payload(
    *,
    guidance_facts: ChildGuidanceFacts,
    segment_rows: Sequence[models.ChildSegmentGeneration],
    artifact_generation_id: UUID | None = None,
) -> dict[str, Any]:
    """Assemble verified rows in contract order without rerunning deterministic calculations."""

    input_by_key = {item.section_key: item for item in build_child_section_inputs(guidance_facts)}
    output_generation_id = artifact_generation_id or guidance_facts.generation_id
    allowed_generation_ids = (
        {guidance_facts.generation_id}
        if artifact_generation_id is None
        else {guidance_facts.generation_id, artifact_generation_id}
    )
    row_by_key: dict[str, models.ChildSegmentGeneration] = {}
    for row in segment_rows:
        if row.child_profile_id != guidance_facts.child_id or row.generation_id not in allowed_generation_ids:
            raise ChildNarrativeValidationError("segment lineage mismatch")
        if row.section_key not in input_by_key:
            raise ChildNarrativeValidationError("unknown segment section")
        if row.section_key in row_by_key:
            raise ChildNarrativeValidationError("duplicate segment section")
        row_by_key[row.section_key] = row

    sections: list[dict[str, Any]] = []
    section_generations: list[dict[str, Any]] = []
    failed_sections: list[str] = []
    omitted_sections: list[str] = []
    missing_sections: list[str] = []
    for section_key in SECTION_METADATA:
        section_input = input_by_key[section_key]
        segment_row = row_by_key.get(section_key)
        if segment_row is None:
            missing_sections.append(section_key)
            continue
        metadata = _verify_generation_metadata(row=segment_row, section_input=section_input)
        if segment_row.status not in {"ready", "not_applicable", "failed"}:
            raise ChildNarrativeValidationError("invalid segment status")
        if segment_row.status == "not_applicable":
            if (
                section_input.owned_facts
                or segment_row.content is not None
                or segment_row.evidence_refs
                or segment_row.error_code is not None
                or "output" in segment_row.diagnostics
                or "output_hash" in segment_row.diagnostics
            ):
                raise ChildNarrativeValidationError("invalid not-applicable segment")
            if (
                segment_row.diagnostics.get("attempts") != 0
                or segment_row.diagnostics.get("reason") != "no_owned_facts"
            ):
                raise ChildNarrativeValidationError("invalid not-applicable metadata")
            omitted_sections.append(section_key)
            section_generations.append({"section_key": section_key, "status": "not_applicable", **metadata})
            continue
        if segment_row.status == "failed":
            failed_attempts = segment_row.diagnostics.get("attempts")
            disabled = segment_row.error_code == "child_narrative_disabled"
            valid_attempts = type(failed_attempts) is int and (
                (failed_attempts == 0 and metadata["provider"] == "disabled")
                if disabled
                else 1 <= failed_attempts <= section_input.maximum_attempts
            )
            if (
                segment_row.content is not None
                or segment_row.evidence_refs
                or segment_row.error_code
                not in {
                    "child_narrative_disabled",
                    "child_narrative_validation_failure",
                    "child_narrative_provider_failure",
                    "child_narrative_provider_outcome_unknown",
                }
                or not valid_attempts
                or not _error_type_is_valid(segment_row.diagnostics.get("error_type"))
                or "output" in segment_row.diagnostics
                or "output_hash" in segment_row.diagnostics
            ):
                raise ChildNarrativeValidationError("invalid failed segment")
            failed_sections.append(section_key)
            section_generations.append({"section_key": section_key, "status": segment_row.status, **metadata})
            continue
        if not section_input.owned_facts:
            raise ChildNarrativeValidationError("empty section cannot be ready")
        raw_output = segment_row.diagnostics.get("output")
        if not isinstance(raw_output, dict):
            raise ChildNarrativeValidationError("ready segment lacks structured output")
        try:
            output = validate_segment_output(
                output=ChildSegmentOutput.model_validate(raw_output),
                section_input=section_input,
                guidance_facts=guidance_facts,
            )
        except ValidationError as exc:
            raise ChildNarrativeValidationError("stored segment output schema is invalid") from exc
        output_payload = output.model_dump(mode="json")
        if segment_row.diagnostics.get("output_hash") != _stable_hash(output_payload):
            raise ChildNarrativeValidationError("segment output hash mismatch")
        fact_id_map = _section_fact_id_map(guidance_facts=guidance_facts, section_key=section_key)
        canonical_refs = [fact_id_map[reference] for reference in output.cited_fact_ids]
        if segment_row.content != output.body or segment_row.evidence_refs != canonical_refs:
            raise ChildNarrativeValidationError("persisted segment does not match validated output")
        sections.append(output_payload)
        section_generations.append({"section_key": section_key, "status": "ready", **metadata})

    status = "ready" if not failed_sections and not missing_sections else "partial"
    return {
        "contract_version": "child_report_narrative_v1",
        "generation_id": str(output_generation_id),
        "source_generation_id": str(guidance_facts.generation_id),
        "child_id": str(guidance_facts.child_id),
        "age_snapshot_id": str(guidance_facts.age_snapshot_id),
        "core_report_version": guidance_facts.core_report_version,
        "prompt_version": CHILD_PROMPT_VERSION,
        "status": status,
        "section_order": list(SECTION_METADATA),
        "sections": sections,
        "section_generations": section_generations,
        "failed_sections": failed_sections,
        "omitted_sections": omitted_sections,
        "missing_sections": missing_sections,
    }
