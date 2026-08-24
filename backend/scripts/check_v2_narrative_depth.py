"""Local Astrotype v2 narrative-depth smoke command.

Default mode validates simulated fixture text. Real-provider mode is intentionally
optional and must be wired by the caller after provider credentials/quota are
confirmed; this script never claims real LLM quality from simulated output.
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from app.modules.astrotype_v2.schemas import ReportSegmentOutputV2, SectionRenderInputV2, SectionThemeInputV2
from app.modules.astrotype_v2.segment_validation import SegmentValidationError, validate_segment_output_v2

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = (
    ROOT / "tests" / "fixtures" / "astrotype_v2" / "narrative_depth" / "positive_simulated_core_pattern.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Astrotype v2 narrative depth fixtures.")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--mode", choices=("simulated_llm", "real_provider"), default="simulated_llm")
    args = parser.parse_args()

    if args.mode == "real_provider":
        print(
            "mode=real_provider status=skipped "
            "reason=provider invocation is optional and not configured in this smoke script"
        )
        return 0

    fixture = json.loads(args.fixture.read_text())
    mode = fixture.get("generation_mode", "unknown")
    output = ReportSegmentOutputV2.model_validate(fixture["segment"])
    try:
        validate_segment_output_v2(output=output, section_input=_section_input())
    except SegmentValidationError as exc:
        print(f"mode={mode} status=failed error={exc}")
        return 1
    print(f"mode={mode} status=passed section={output.section_id} words={len(output.body.split())}")
    return 0


def _section_input() -> SectionRenderInputV2:
    return SectionRenderInputV2(
        chart_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        source_version="v2.0",
        section_id="core_pattern",
        section_title="Ядро личности",
        section_purpose="local narrative-depth smoke",
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


if __name__ == "__main__":
    raise SystemExit(main())
