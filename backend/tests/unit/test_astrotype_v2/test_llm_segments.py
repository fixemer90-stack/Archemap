"""Contract tests for Astrotype v2 LLM segment prompts, validation, and runner lifecycle."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.modules.astrotype_v2.outline import build_report_outline_v2
from app.modules.astrotype_v2.schemas import ReportSegmentOutputV2, SectionRenderInputV2
from app.modules.astrotype_v2.segment_inputs import build_section_render_inputs_v2
from app.modules.astrotype_v2.synthesis import NatalSynthesisV2, SynthesisThemeV2


class FakeSegmentProvider:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, SectionRenderInputV2]] = []
        self.model_name = "fake-segment-model"
        self.provider_name = "fake"

    async def generate_segment(self, *, prompt: str, section_input: SectionRenderInputV2) -> dict[str, Any]:
        self.calls.append((prompt, section_input))
        return self.responses.pop(0)


def _theme(theme_id: str, section: str, evidence_id: str) -> SynthesisThemeV2:
    return SynthesisThemeV2(
        id=theme_id,
        title=theme_id,
        summary=f"{theme_id} summary",
        primary_section=section,
        fact_keys=(f"fact:{theme_id}",),
        evidence_ids=(evidence_id,),
        weight=0.9,
        confidence=1.0,
        polarity=None,
        fact_type="placement",
    )


def _section_input() -> SectionRenderInputV2:
    chart_id = uuid.uuid4()
    synthesis = NatalSynthesisV2(
        chart_id=chart_id,
        source_version="v2.0",
        dominant_themes=(
            _theme("theme:core:sun", "core_pattern", "ev:sun"),
            _theme("theme:mind:mercury", "perception_and_mind", "ev:mercury"),
            _theme("theme:emotion:moon", "emotional_regulation", "ev:moon"),
            _theme("theme:agency:mars", "agency_and_desire", "ev:mars"),
        ),
        input_fact_keys=[
            "fact:theme:agency:mars",
            "fact:theme:core:sun",
            "fact:theme:emotion:moon",
            "fact:theme:mind:mercury",
        ],
    )
    outline = build_report_outline_v2(synthesis=synthesis, source_version="v2.0")
    return build_section_render_inputs_v2(outline=outline, synthesis=synthesis)[0]


def _valid_long_output(section_id: str = "core_pattern") -> dict[str, Any]:
    return {
        "contract_version": "report_segment_output_v2",
        "section_id": section_id,
        "title": "Ядро личности",
        "body": (
            "Первый развёрнутый абзац подробно раскрывает тему Солнца и показывает внутренний механизм.\n\n"
            "Второй абзац опирается на evidence ev:sun и не сводит раздел к короткому резюме.\n\n"
            "Третий абзац продолжает объяснение, сохраняя связность и конкретность без общих клише."
        ),
        "covered_theme_ids": ["theme:core:sun"],
        "evidence_ids": ["ev:sun"],
        "continuation_complete": True,
        "continuation_cursor": None,
        "notes": [],
    }


def test_build_segment_prompt_requires_expanded_json_grounded_in_one_section_without_low_caps() -> None:
    from app.modules.astrotype_v2.llm_segments import build_segment_prompt

    prompt = build_segment_prompt(_section_input())
    lowered = prompt.lower()

    assert "report_segment_output_v2" in prompt
    assert "write only this section" in lowered
    assert "cover every owned theme" in lowered
    assert "deep, expanded" in lowered
    assert "provided json" in lowered
    assert "forbidden_theme_ids" in prompt
    assert "deterministic lower calculation layer" in lowered
    assert "socionics" in lowered
    assert "archetype" in lowered

    forbidden_low_caps = ("be brief", "short summary", "max 3 paragraphs", "keep under", "concise overview only")
    for fragment in forbidden_low_caps:
        assert fragment not in lowered


def test_validate_segment_output_rejects_unknown_evidence_forbidden_theme_and_shallow_text() -> None:
    from app.modules.astrotype_v2.segment_validation import SegmentValidationError, validate_segment_output_v2

    section_input = _section_input()
    valid = ReportSegmentOutputV2.model_validate(_valid_long_output())
    assert validate_segment_output_v2(output=valid, section_input=section_input) == valid

    with pytest.raises(SegmentValidationError, match="unknown evidence"):
        validate_segment_output_v2(
            output=ReportSegmentOutputV2.model_validate({**_valid_long_output(), "evidence_ids": ["ev:unknown"]}),
            section_input=section_input,
        )

    with pytest.raises(SegmentValidationError, match="forbidden theme"):
        validate_segment_output_v2(
            output=ReportSegmentOutputV2.model_validate(
                {**_valid_long_output(), "covered_theme_ids": [section_input.forbidden_theme_ids[0]]}
            ),
            section_input=section_input,
        )

    with pytest.raises(SegmentValidationError, match="underdeveloped"):
        validate_segment_output_v2(
            output=ReportSegmentOutputV2.model_validate({**_valid_long_output(), "body": "Очень коротко."}),
            section_input=section_input,
        )


def test_validate_segment_output_preserves_long_grounded_section_without_artificial_max_length() -> None:
    from app.modules.astrotype_v2.segment_validation import validate_segment_output_v2

    section_input = _section_input()
    long_body = "\n\n".join(
        f"Развёрнутый абзац {index} подробно раскрывает evidence ev:sun и тему theme:core:sun."
        for index in range(1, 18)
    )
    output = ReportSegmentOutputV2.model_validate({**_valid_long_output(), "body": long_body})

    assert validate_segment_output_v2(output=output, section_input=section_input).body == long_body


@pytest.mark.asyncio
async def test_run_segment_generation_persists_segment_status_and_retries_only_the_failed_section() -> None:
    from app.modules.astrotype_v2.llm_segments import run_segment_generation_v2

    section_input = _section_input()
    provider = FakeSegmentProvider([_valid_long_output()])

    row = await run_segment_generation_v2(
        provider=provider,
        section_input=section_input,
        outline_id=uuid.uuid4(),
        prompt_version="astrotype_v2_segment_v1",
    )

    assert row.section_key == "core_pattern"
    assert row.status == "ready"
    assert row.provider == "fake"
    assert row.model == "fake-segment-model"
    assert row.prompt_version == "astrotype_v2_segment_v1"
    assert row.payload["request"]["section_id"] == "core_pattern"
    assert row.payload["response"]["covered_theme_ids"] == ["theme:core:sun"]
    assert row.payload["retry_scope"] == "section_only"
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_run_segment_generation_marks_continuation_required_without_truncating_partial_output() -> None:
    from app.modules.astrotype_v2.llm_segments import run_segment_generation_v2

    partial = {**_valid_long_output(), "continuation_complete": False, "continuation_cursor": "part-1"}
    section_input = _section_input()
    provider = FakeSegmentProvider([partial])

    row = await run_segment_generation_v2(
        provider=provider,
        section_input=section_input,
        outline_id=uuid.uuid4(),
        prompt_version="astrotype_v2_segment_v1",
    )

    assert row.status == "continuation_required"
    assert row.payload["response"]["body"] == partial["body"]
    assert row.payload["continuation"]["cursor"] == "part-1"
    assert row.payload["continuation"]["next_request_scope"] == "same_section_only"
