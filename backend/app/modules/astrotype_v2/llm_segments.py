# ruff: noqa: E501,RUF001
"""Prompt construction and segment-level LLM runner for Astrotype v2."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Protocol, cast

from app.modules.astrotype_v2 import models
from app.modules.astrotype_v2.schemas import ReportSegmentOutputV2, SectionRenderInputV2
from app.modules.astrotype_v2.segment_validation import SegmentValidationError, validate_segment_output_v2

DEFAULT_SEGMENT_PROMPT_VERSION = "astrotype_v2_segment_v2_depth"


class SegmentLLMProvider(Protocol):
    """Minimal provider boundary for one v2 report segment."""

    provider_name: str
    model_name: str

    async def generate_segment(self, *, prompt: str, section_input: SectionRenderInputV2) -> dict[str, Any]:
        """Return raw JSON-like data for one section."""
        ...


class StructuredLLMProvider(Protocol):
    """Generic project LLM provider boundary used by existing provider factory."""

    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: Any,
        schema: type[ReportSegmentOutputV2],
    ) -> ReportSegmentOutputV2:
        """Generate and validate a structured model response."""
        ...


class StructuredSegmentProviderAdapter:
    """Adapt the generic provider factory to the v2 segment provider boundary."""

    def __init__(self, *, provider: StructuredLLMProvider, provider_name: str, model_name: str) -> None:
        self._provider = provider
        self.provider_name = provider_name
        self.model_name = model_name

    async def generate_segment(self, *, prompt: str, section_input: SectionRenderInputV2) -> dict[str, Any]:
        response = await self._provider.generate_structured(
            prompt=prompt,
            narrative_input=cast(Any, section_input),
            schema=ReportSegmentOutputV2,
        )
        return response.model_dump(mode="json")


def build_segment_prompt(section_input: SectionRenderInputV2) -> str:
    """Build the system prompt for one upper narrative section."""

    payload_json = json.dumps(section_input.to_payload(), ensure_ascii=False, sort_keys=True)
    length_contract = _section_length_contract(section_input.section_id)
    return f"""
You are writing an Astrotype v2 natal-only personality report segment.

Write only this section: {section_input.section_id} — {section_input.section_title}.
Write a deep psychological reading of this one section, not a broad life overview.
Use only the provided JSON facts, themes, boundaries, and evidence ids.
Return typed JSON matching contract_version report_segment_output_v2.

Depth contract:
- Product depth target: {length_contract}. This is separate from the technical emptiness floor used only to detect malformed empty output.
- Do not shrink, summarize, or compress the section to satisfy provider limits. If provider output is cut, set continuation_complete=false and continuation_cursor.
- Cover every owned theme and every owned evidence id with developed explanation.
- Build the section through this chain: central formula → psychological mechanism → lived manifestation → inner tension or polarity → protective/shadow strategy → mature integrated expression → soft self-check or integration cue.
- Explain inner mechanisms and lived patterns; do not produce generic horoscope filler.
- Do not use placements, aspects, houses, or evidence ids as the section structure; transform technical facts into interpretation.
- Reference themes may be used only for continuity.
- Never expand forbidden_theme_ids.
- Do not render the deterministic lower calculation layer, tables, infographic data or factual-basis appendix.
- Do not invent chart facts, unsupported aspects, houses, planets or evidence ids.
- Do not mention socionics, archetype labels, Model A, function strengths or typology systems.

Output JSON fields:
contract_version, section_id, title, body, covered_theme_ids, evidence_ids,
continuation_complete, continuation_cursor, notes.

Provided JSON:
{payload_json}
""".strip()


def _section_length_contract(section_id: str) -> str:
    if section_id == "core_pattern":
        return "700–1200 words and 6–9 developed paragraphs unless continuation is needed"
    return "450–900 words and 4–7 developed paragraphs unless continuation is needed"


async def run_segment_generation_v2(
    *,
    provider: SegmentLLMProvider,
    section_input: SectionRenderInputV2,
    outline_id: uuid.UUID,
    prompt_version: str = DEFAULT_SEGMENT_PROMPT_VERSION,
) -> models.ReportSegmentGeneration:
    """Run one section request and return a persistable segment generation row."""

    prompt = build_segment_prompt(section_input)
    validation_error: SegmentValidationError | None = None
    for attempt in range(2):
        retry_prompt = prompt
        if validation_error is not None:
            retry_prompt = (
                f"{prompt}\n\n"
                "Your previous JSON failed validation. Return the same section again as valid JSON only. "
                f"Validation error: {validation_error}. "
                "Do not change section_id. Use only allowed evidence_ids and covered_theme_ids. "
                "If the body was underdeveloped, preserve the same product depth contract: "
                f"{_section_length_contract(section_input.section_id)}. "
                "Include mechanism, lived manifestation, tension, protection or shadow, mature expression, and a soft self-check cue."
            )
        raw_response = await provider.generate_segment(prompt=retry_prompt, section_input=section_input)
        parsed = ReportSegmentOutputV2.model_validate(raw_response)
        try:
            validated = validate_segment_output_v2(output=parsed, section_input=section_input)
            break
        except SegmentValidationError as exc:
            validation_error = exc
            if attempt >= 1:
                raise
    else:  # pragma: no cover - loop always exits or raises
        raise SegmentValidationError("segment validation retry exhausted")
    status = "ready" if validated.continuation_complete else "continuation_required"

    request_payload = section_input.to_payload()
    response_payload = validated.model_dump(mode="json")
    return models.ReportSegmentGeneration(
        chart_id=section_input.chart_id,
        outline_id=outline_id,
        section_key=section_input.section_id,
        status=status,
        provider=provider.provider_name,
        model=provider.model_name,
        prompt_version=prompt_version,
        payload={
            "request": request_payload,
            "request_hash": _stable_hash(request_payload),
            "prompt_hash": _stable_hash({"prompt": prompt}),
            "response": response_payload,
            "response_hash": _stable_hash(response_payload),
            "retry_scope": "section_only",
            "continuation": _continuation_payload(validated),
        },
        error=None,
    )


def _continuation_payload(output: ReportSegmentOutputV2) -> dict[str, Any]:
    if output.continuation_complete:
        return {"required": False, "cursor": None, "next_request_scope": None}
    return {
        "required": True,
        "cursor": output.continuation_cursor,
        "next_request_scope": "same_section_only",
    }


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
