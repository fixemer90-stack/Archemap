"""Fixture-backed narrative depth smoke checks for Astrotype v2."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, cast

import pytest

from app.modules.astrotype_v2.schemas import ReportSegmentOutputV2, SectionRenderInputV2, SectionThemeInputV2
from app.modules.astrotype_v2.segment_validation import SegmentValidationError, validate_segment_output_v2

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "astrotype_v2" / "narrative_depth"


def _section_input() -> SectionRenderInputV2:
    return SectionRenderInputV2(
        chart_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        source_version="v2.0",
        section_id="core_pattern",
        section_title="Ядро личности",
        section_purpose="depth fixture smoke",
        owned_themes=[
            SectionThemeInputV2(
                id="theme:core:sun",
                title="Sun theme",
                summary="Grounded solar summary",
                fact_keys=["fact:sun"],
                evidence_ids=["ev:sun"],
                weight=0.9,
                confidence=1.0,
            )
        ],
        reference_themes=[],
        forbidden_theme_ids=[],
        evidence_ids=["ev:sun"],
        already_explained={},
        style_contract={},
        depth_contract={},
        continuation_policy={"continuation_supported": True},
    )


def _load_fixture(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((FIXTURE_DIR / name).read_text()))


def test_positive_simulated_llm_fixture_passes_depth_validator_and_names_mode() -> None:
    fixture = _load_fixture("positive_simulated_core_pattern.json")
    assert fixture["generation_mode"] == "simulated_llm"

    output = ReportSegmentOutputV2.model_validate(fixture["segment"])

    assert validate_segment_output_v2(output=output, section_input=_section_input()) == output


@pytest.mark.parametrize(
    ("fixture_name", "expected_error"),
    [
        ("negative_shallow_80_words.json", "underdeveloped"),
        ("negative_raw_fact_dump.json", "raw fact dump"),
        ("negative_generic_filler.json", "generic filler"),
        ("negative_missing_mature_expression.json", "missing depth moves"),
        ("negative_missing_lived_manifestation.json", "missing depth moves"),
    ],
)
def test_negative_depth_fixtures_fail_for_expected_reason(fixture_name: str, expected_error: str) -> None:
    fixture = _load_fixture(fixture_name)
    assert fixture["generation_mode"] == "simulated_llm"
    output = ReportSegmentOutputV2.model_validate(fixture["segment"])

    with pytest.raises(SegmentValidationError, match=expected_error):
        validate_segment_output_v2(output=output, section_input=_section_input())
