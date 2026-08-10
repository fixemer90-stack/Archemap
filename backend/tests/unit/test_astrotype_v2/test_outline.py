"""Contract tests for Astrotype v2 deterministic report outline planning."""

from __future__ import annotations

import uuid
from pathlib import Path

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
        _theme(theme_id="theme:agency:mars", primary_section="agency_and_desire", weight=0.6, evidence_id="ev:mars"),
        _theme(
            theme_id="theme:relations:venus",
            primary_section="relationships_and_intimacy",
            weight=0.5,
            evidence_id="ev:venus",
        ),
        _theme(theme_id="theme:growth:saturn", primary_section="growth_vector", weight=0.4, evidence_id="ev:saturn"),
    )
    return NatalSynthesisV2(
        chart_id=chart_id,
        source_version="v2.0",
        dominant_themes=themes,
        input_fact_keys=sorted(theme.fact_keys[0] for theme in themes),
    )


def test_score_theme_clusters_groups_themes_by_primary_section_with_stable_scores() -> None:
    from app.modules.astrotype_v2.outline import score_theme_clusters

    chart_id = uuid.uuid4()
    clusters = score_theme_clusters(_synthesis(chart_id))

    assert [cluster.section_id for cluster in clusters] == [
        "core_pattern",
        "perception_and_mind",
        "emotional_regulation",
        "agency_and_desire",
        "relationships_and_intimacy",
        "growth_vector",
    ]
    assert clusters[0].score == 0.9
    assert clusters[0].theme_ids == ("theme:core:sun",)
    assert clusters[0].evidence_ids == ("ev:sun",)


def test_build_report_outline_v2_assigns_every_theme_to_exactly_one_owner_and_limits_references() -> None:
    from app.modules.astrotype_v2.outline import build_report_outline_v2

    chart_id = uuid.uuid4()
    outline = build_report_outline_v2(synthesis=_synthesis(chart_id), source_version="v2.0")

    assert outline.contract_version == "report_outline_v2"
    assert outline.chart_id == chart_id
    assert outline.section_keys == [
        "core_pattern",
        "perception_and_mind",
        "emotional_regulation",
        "agency_and_desire",
        "relationships_and_intimacy",
        "growth_vector",
    ]

    owned_theme_ids = [theme_id for section in outline.sections for theme_id in section.owned_theme_ids]
    assert sorted(owned_theme_ids) == sorted(theme.id for theme in _synthesis(chart_id).dominant_themes)
    assert len(owned_theme_ids) == len(set(owned_theme_ids))

    all_theme_ids = set(owned_theme_ids)
    for section in outline.sections:
        assert not set(section.owned_theme_ids) & set(section.reference_theme_ids)
        assert not set(section.owned_theme_ids) & set(section.forbidden_theme_ids)
        assert not set(section.reference_theme_ids) & set(section.forbidden_theme_ids)
        scoped_theme_ids = (
            set(section.owned_theme_ids) | set(section.reference_theme_ids) | set(section.forbidden_theme_ids)
        )
        assert scoped_theme_ids == all_theme_ids
        assert len(section.reference_theme_ids) <= 2
        assert set(section.reference_theme_ids) != all_theme_ids

    payload = outline.to_payload()
    assert payload["sections"][0]["id"] == "core_pattern"
    assert "theme:core:sun" in payload["sections"][0]["owned_theme_ids"]
    assert "socionics" not in str(payload).lower()
    assert "function_strength" not in str(payload).lower()
    assert "model_a" not in str(payload).lower()


def test_build_report_outline_row_returns_persistable_v2_orm_row() -> None:
    from app.modules.astrotype_v2.outline import build_report_outline_row

    chart_id = uuid.uuid4()
    row = build_report_outline_row(synthesis=_synthesis(chart_id), source_version="v2.0")

    assert row.chart_id == chart_id
    assert row.status == "ready"
    assert row.section_keys == [
        "core_pattern",
        "perception_and_mind",
        "emotional_regulation",
        "agency_and_desire",
        "relationships_and_intimacy",
        "growth_vector",
    ]
    assert row.outline["contract_version"] == "report_outline_v2"


def test_render_debug_outline_payload_is_deterministic_and_contains_no_llm_fields() -> None:
    from app.modules.astrotype_v2.outline import build_report_outline_v2, render_debug_outline_payload

    chart_id = uuid.uuid4()
    synthesis = _synthesis(chart_id)
    outline = build_report_outline_v2(synthesis=synthesis, source_version="v2.0")

    first = render_debug_outline_payload(outline=outline, synthesis=synthesis)
    second = render_debug_outline_payload(outline=outline, synthesis=synthesis)

    assert first == second
    assert first["contract_version"] == "report_outline_debug_v2"
    assert first["sections"][0]["owned_themes"][0]["id"] == "theme:core:sun"
    assert "prompt" not in str(first).lower()
    assert "llm" not in str(first).lower()


def test_outline_module_does_not_import_legacy_socionics_or_report_narratives() -> None:
    outline_path = ROOT / "app" / "modules" / "astrotype_v2" / "outline.py"
    source = outline_path.read_text()

    forbidden_fragments = (
        "socionics",
        "function_strengths",
        "Model A",
        "model_a",
        "report_narratives",
        "build_narrative_input",
        "SocionicsSummary",
    )
    for fragment in forbidden_fragments:
        assert fragment not in source
