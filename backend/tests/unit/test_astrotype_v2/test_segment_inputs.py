"""Contract tests for Astrotype v2 SectionRenderInputV2 builders."""

from __future__ import annotations

import uuid
from pathlib import Path

from app.modules.astrotype_v2.outline import build_report_outline_v2
from app.modules.astrotype_v2.synthesis import NatalSynthesisV2, SynthesisThemeV2

ROOT = Path(__file__).resolve().parents[3]


def _theme(
    *,
    theme_id: str,
    primary_section: str,
    weight: float,
    evidence_id: str,
) -> SynthesisThemeV2:
    return SynthesisThemeV2(
        id=theme_id,
        title=theme_id,
        summary=f"{theme_id} summary",
        primary_section=primary_section,
        fact_keys=(f"fact:{theme_id}",),
        evidence_ids=(evidence_id,),
        weight=weight,
        confidence=1.0,
        polarity=None,
        fact_type="placement",
        psychological_mechanism=f"{theme_id} mechanism",
        lived_manifestation=f"{theme_id} manifestation",
        inner_tension=f"{theme_id} tension",
        protective_strategy=f"{theme_id} protection",
        immature_expression=f"{theme_id} immature",
        mature_expression=f"{theme_id} mature",
        integration_question=f"{theme_id} question",
        evidence_strength="strong",
    )


def _synthesis(chart_id: uuid.UUID) -> NatalSynthesisV2:
    themes = (
        _theme(theme_id="theme:core:sun", primary_section="core_pattern", weight=0.9, evidence_id="ev:sun"),
        _theme(
            theme_id="theme:mind:mercury",
            primary_section="perception_and_mind",
            weight=0.8,
            evidence_id="ev:mercury",
        ),
        _theme(
            theme_id="theme:emotion:moon",
            primary_section="emotional_regulation",
            weight=0.7,
            evidence_id="ev:moon",
        ),
    )
    return NatalSynthesisV2(
        chart_id=chart_id,
        source_version="v2.0",
        dominant_themes=themes,
        input_fact_keys=sorted(theme.fact_keys[0] for theme in themes),
    )


def test_build_section_render_inputs_v2_creates_one_curated_input_per_outline_section() -> None:
    from app.modules.astrotype_v2.segment_inputs import build_section_render_inputs_v2

    chart_id = uuid.uuid4()
    synthesis = _synthesis(chart_id)
    outline = build_report_outline_v2(synthesis=synthesis, source_version="v2.0")

    inputs = build_section_render_inputs_v2(outline=outline, synthesis=synthesis)

    assert [item.section_id for item in inputs] == outline.section_keys
    core = inputs[0]
    assert core.contract_version == "section_render_input_v2"
    assert core.chart_id == chart_id
    assert core.section_id == "core_pattern"
    assert core.section_title == "Ядро личности"
    assert core.owned_themes[0].id == "theme:core:sun"
    assert core.owned_themes[0].psychological_mechanism
    assert core.owned_themes[0].lived_manifestation
    assert core.owned_themes[0].inner_tension
    assert core.owned_themes[0].protective_strategy
    assert core.owned_themes[0].mature_expression
    assert core.owned_themes[0].integration_question
    assert [theme.id for theme in core.reference_themes] == [
        "theme:emotion:moon",
        "theme:mind:mercury",
    ]
    assert "theme:core:sun" not in core.forbidden_theme_ids
    assert "theme:core:sun" in core.already_explained["owned_theme_ids"]
    assert core.evidence_ids == ["ev:sun"]


def test_section_render_input_payload_has_depth_and_continuation_contract_without_low_length_caps() -> None:
    from app.modules.astrotype_v2.segment_inputs import build_section_render_inputs_v2

    chart_id = uuid.uuid4()
    synthesis = _synthesis(chart_id)
    outline = build_report_outline_v2(synthesis=synthesis, source_version="v2.0")

    payload = build_section_render_inputs_v2(outline=outline, synthesis=synthesis)[0].to_payload()

    assert payload["depth_contract"]["mode"] == "expanded_section"
    assert payload["depth_contract"]["coverage"] == "cover every owned theme and evidence id with developed prose"
    assert payload["depth_contract"]["technical_emptiness_floor"] == {"paragraphs": 3, "words": 80}
    assert payload["depth_contract"]["section_targets"]["core_pattern"] == {"words": "700-1200", "paragraphs": "6-9"}
    assert "psychological mechanism" in payload["depth_contract"]["required_moves"]
    assert payload["continuation_policy"]["continuation_supported"] is True
    assert payload["continuation_policy"]["retry_scope"] == "section_only"

    forbidden_low_caps = ("max_chars", "max_paragraphs", "brief", "short summary", "concise overview")
    lowered = str(payload).lower()
    for fragment in forbidden_low_caps:
        assert fragment not in lowered


def test_segment_input_builder_source_is_legacy_isolated_and_does_not_import_llm_runtime() -> None:
    source = (ROOT / "app" / "modules" / "astrotype_v2" / "segment_inputs.py").read_text()

    forbidden_fragments = (
        "socionics",
        "function_strengths",
        "model_a",
        "report_narratives",
        "build_narrative_input",
        "get_llm_provider",
        "OpenRouterProvider",
        "DeepSeekProvider",
    )
    for fragment in forbidden_fragments:
        assert fragment not in source
