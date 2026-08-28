"""Regression tests for v2 section evidence grounding."""

from __future__ import annotations

import uuid

from app.modules.astrotype_v2 import models


def _fact(*, chart_id: uuid.UUID, fact_type: str, fact_key: str, title: str, section_hint: str) -> models.NatalFact:
    return models.NatalFact(
        chart_id=chart_id,
        fact_type=fact_type,
        fact_key=fact_key,
        title=title,
        summary=f"{title} summary",
        weight=1.0,
        confidence=1.0,
        polarity=None,
        section_hint=section_hint,
        payload={"evidence_ids": [f"ev:{fact_key}"]},
        source_version="v2.0",
    )


def test_source_type_hints_are_semantically_distributed_across_report_sections() -> None:
    from app.modules.astrotype_v2.synthesis import build_natal_synthesis_v2

    chart_id = uuid.uuid4()
    facts = [
        _fact(
            chart_id=chart_id,
            fact_type="placement",
            fact_key="placement:sun:taurus:house_12",
            title="Sun in Taurus, house 12",
            section_hint="placements",
        ),
        _fact(
            chart_id=chart_id,
            fact_type="placement",
            fact_key="placement:mercury:gemini:house_3",
            title="Mercury in Gemini, house 3",
            section_hint="placements",
        ),
        _fact(
            chart_id=chart_id,
            fact_type="placement",
            fact_key="placement:moon:cancer:house_4",
            title="Moon in Cancer, house 4",
            section_hint="placements",
        ),
        _fact(
            chart_id=chart_id,
            fact_type="placement",
            fact_key="placement:mars:aries:house_1",
            title="Mars in Aries, house 1",
            section_hint="placements",
        ),
        _fact(
            chart_id=chart_id,
            fact_type="placement",
            fact_key="placement:venus:libra:house_7",
            title="Venus in Libra, house 7",
            section_hint="placements",
        ),
        _fact(
            chart_id=chart_id,
            fact_type="aspect",
            fact_key="aspect:saturn:jupiter:trine",
            title="Saturn trine Jupiter",
            section_hint="aspects",
        ),
        _fact(
            chart_id=chart_id,
            fact_type="balance",
            fact_key="balance:element:fire",
            title="Fire emphasis",
            section_hint="balances",
        ),
    ]

    synthesis = build_natal_synthesis_v2(chart_id=chart_id, facts=facts)
    sections = {theme.primary_section for theme in synthesis.dominant_themes}

    assert sections >= {
        "core_pattern",
        "perception_and_mind",
        "emotional_regulation",
        "agency_and_desire",
        "relationships_and_intimacy",
        "growth_vector",
    }


def test_outline_marks_empty_sections_as_bridged_or_skipped_before_llm_inputs() -> None:
    from app.modules.astrotype_v2.outline import build_report_outline_v2
    from app.modules.astrotype_v2.segment_inputs import build_section_render_inputs_v2
    from app.modules.astrotype_v2.synthesis import NatalSynthesisV2, SynthesisThemeV2

    chart_id = uuid.uuid4()
    synthesis = NatalSynthesisV2(
        chart_id=chart_id,
        source_version="v2.0",
        dominant_themes=(
            SynthesisThemeV2(
                id="theme:core:sun",
                title="Sun core",
                summary="Sun core summary",
                primary_section="core_pattern",
                fact_keys=("placement:sun:aries:house_1",),
                evidence_ids=("ev:sun",),
                weight=1.0,
                confidence=1.0,
            ),
        ),
        input_fact_keys=["placement:sun:aries:house_1"],
    )

    outline = build_report_outline_v2(synthesis=synthesis)
    payload_by_section = {section["id"]: section for section in outline.to_payload()["sections"]}

    assert payload_by_section["core_pattern"]["grounding_status"] == "ready"
    assert payload_by_section["relationships_and_intimacy"]["grounding_status"] == "skipped"

    inputs = build_section_render_inputs_v2(outline=outline, synthesis=synthesis)
    assert all(item.evidence_ids for item in inputs)
    assert "relationships_and_intimacy" not in {item.section_id for item in inputs}
