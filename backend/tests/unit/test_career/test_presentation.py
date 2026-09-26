from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
FIXTURE_PATH = ROOT / "contracts" / "fixtures" / "career-report-read-v1-parity.json"


def _fixture() -> dict[str, Any]:
    value: object = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_backend_presentation_matches_shared_semantic_manifest() -> None:
    from app.modules.career.presentation import build_career_report_presentation

    fixture = _fixture()

    assert build_career_report_presentation(fixture["payload"]) == fixture["expected_manifest"]


def test_presentation_keeps_all_narrative_slots_pending_for_deterministic_ready() -> None:
    from app.modules.career.presentation import build_career_report_presentation

    payload = _fixture()["payload"]
    payload["status"] = "deterministic_ready"
    payload["sections"] = []
    payload["section_states"] = []

    manifest = build_career_report_presentation(payload)
    narrative = [block for block in manifest["blocks"] if block["kind"] == "narrative"]

    assert len(narrative) == 10
    assert {block["status"] for block in narrative} == {"pending"}
    assert manifest["notice"]["kind"] == "deterministic_ready"
    assert [block["kind"] for block in manifest["blocks"][:10]] == ["narrative"] * 10
    assert manifest["blocks"][10]["kind"] == "dimensions"


def test_presentation_keeps_progress_notice_while_sections_are_generating() -> None:
    from app.modules.career.presentation import build_career_report_presentation

    payload = _fixture()["payload"]
    payload["status"] = "generating_sections"

    manifest = build_career_report_presentation(payload)

    assert manifest["notice"]["kind"] == "deterministic_ready"


def test_pdf_renders_the_shared_manifest_in_semantic_order() -> None:
    from app.modules.career.pdf import render_career_report_html

    html = render_career_report_html(report_payload=_fixture()["payload"], profile_name="Алина")

    keys = [
        "professional_summary",
        "work_style",
        "strengths",
        "decision_making",
        "leadership_and_influence",
        "optimal_environment",
        "risk_environment",
        "career_archetypes",
        "role_families",
        "career_paths",
        "dimensions",
        "contradictions",
        "context",
        "roles",
        "technical_basis",
    ]
    positions = [html.index(f'data-presentation-key="{key}"') for key in keys]

    assert positions == sorted(positions)
    assert "Industry: regulated" in html
    assert "motivation_score" not in html
    assert "39" in html
