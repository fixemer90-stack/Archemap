from __future__ import annotations

import copy
from datetime import date
from typing import Any
from uuid import uuid4

import pytest
from tests.unit.test_child.test_narrative_pipeline import _facts

from app.modules.child import models
from app.modules.child.narrative import (
    MockChildSegmentProvider,
    build_child_section_inputs,
    run_child_segment_generation,
)
from app.modules.child.presentation import compose_child_report_presentation
from app.modules.child.prompts.v1 import SECTION_METADATA
from app.modules.child.repository import ChildLineageMismatchError


@pytest.mark.asyncio
@pytest.mark.parametrize("version", ["legacy", "current", "v3"])
async def test_child_web_pdf_manifest_preserves_order_and_only_validated_narrative(version: str) -> None:
    from tests.unit.test_child.test_content_v2 import _middle_facts

    facts = (
        _facts()
        if version == "legacy"
        else _middle_facts(contract_version="child-guidance-facts-v3" if version == "v3" else "child-guidance-facts-v2")
    )
    report = models.ChildReport(
        id=uuid4(),
        child_profile_id=facts.child_id,
        generation_id=facts.generation_id,
        version=1,
        presentation_manifest={
            "contract_version": "child_report_presentation_v1",
            "section_order": list(SECTION_METADATA),
            "age_snapshot_id": str(facts.age_snapshot_id),
        },
    )
    age = models.ChildAgeSnapshot(
        id=facts.age_snapshot_id,
        child_profile_id=facts.child_id,
        as_of_date=date(2026, 10, 22),
        age_years=5,
        age_months=4,
        age_days=1,
        age_stage="3-6",
        age_rules_version="child-age-mvp-1",
        input_hash="a" * 64,
    )
    fallback = compose_child_report_presentation(
        report=report,
        facts=facts,
        age_snapshot=age,
        segment_rows=(),
        generation_status="deterministic_ready",
        current_local_date=date(2026, 10, 23),
    )
    for section in fallback["sections"]:
        assert len(section["actions"]) == len(set(section["actions"]))
    segments = [
        await run_child_segment_generation(
            provider=MockChildSegmentProvider(), section_input=item, guidance_facts=facts
        )
        for item in build_child_section_inputs(facts)
    ]
    presentation = compose_child_report_presentation(
        report=report,
        facts=facts,
        age_snapshot=age,
        segment_rows=segments,
        generation_status="ready",
        current_local_date=date(2026, 10, 23),
    )
    assert presentation["contract_version"] == "child_report_presentation_v1"
    assert [item["key"] for item in presentation["sections"]] == list(SECTION_METADATA)
    assert presentation["metadata"]["age_snapshot_id"] == str(age.id)
    assert presentation["age"]["stale"] is True
    assert presentation["age"]["as_of_date"] == "2026-10-22"
    assert any(item["body"] for item in presentation["sections"])
    assert all(not item["actions"] for item in presentation["sections"] if item["body"])
    assert all("provider" not in item for item in presentation["sections"])
    assert "raw_answers" not in str(presentation)
    if version == "current":
        indicators = presentation["technical_basis"]["source_indicators"]
        assert any(item["source_kind"] == "parent_style" and item["score"] == 57 for item in indicators)
        assert any(item["source_kind"] == "child_needs" and item["dimension"] == "recognition" for item in indicators)
        assert all("evidence_refs" not in item for item in indicators)

    from app.modules.child.pdf import render_child_report_html, render_child_report_pdf

    html = render_child_report_html(presentation)
    assert presentation["quality"]["status"] == "limited"
    assert presentation["quality"]["omitted_sections"]
    assert 'data-quality-status="limited"' in html
    assert "Часть разделов" in html
    omitted = [item for item in presentation["sections"] if item["status"] == "not_applicable"]
    assert omitted
    for item in omitted:
        block = html.split(f'data-section-key="{item["key"]}">', 1)[1].split("</section>", 1)[0]
        assert "Для отдельного пояснения пока недостаточно устойчивых оснований." in block
    if version == "v3":
        assert html.count("Это не оценка способностей и не фиксированная черта ребёнка") == 1
    assert "insufficient_section_evidence" not in html
    legacy_without_quality = {key: value for key, value in presentation.items() if key != "quality"}
    assert "data-quality-status" not in render_child_report_html(legacy_without_quality)
    assert [html.index(f'data-section-key="{key}"') for key in SECTION_METADATA] == sorted(
        html.index(f'data-section-key="{key}"') for key in SECTION_METADATA
    )
    for item in presentation["sections"]:
        if item["body"]:
            assert item["body"] in html
        assert item["confidence_note"] in html
    assert f"{age.age_years} лет · {age.age_months} мес. · {age.age_days} дн." in html
    assert 'name="child-core-version" content="1"' in html
    assert f'name="child-age-snapshot-id" content="{age.id}"' in html
    assert 'name="child-age-as-of" content="2026-10-22"' in html
    assert render_child_report_pdf(presentation).startswith(b"%PDF-")

    segments[1].content = "unsupported inserted prose"
    with pytest.raises(ChildLineageMismatchError):
        compose_child_report_presentation(
            report=report,
            facts=facts,
            age_snapshot=age,
            segment_rows=segments,
            generation_status="ready",
            current_local_date=date(2026, 10, 23),
        )


@pytest.mark.parametrize("mutation", ["version", "order", "age", "foreign"])
def test_child_manifest_rejects_mixed_or_unknown_presentation_lineage(mutation: str) -> None:
    facts = _facts()
    manifest: dict[str, Any] = {
        "contract_version": "child_report_presentation_v1",
        "section_order": list(SECTION_METADATA),
        "age_snapshot_id": str(facts.age_snapshot_id),
    }
    if mutation == "version":
        manifest["contract_version"] = "unrecognized"
    if mutation == "order":
        manifest["section_order"] = list(reversed(list(SECTION_METADATA)))
    if mutation == "age":
        manifest["age_snapshot_id"] = str(uuid4())
    report = models.ChildReport(
        id=uuid4(),
        child_profile_id=uuid4() if mutation == "foreign" else facts.child_id,
        generation_id=facts.generation_id,
        version=1,
        presentation_manifest=manifest,
    )
    age = models.ChildAgeSnapshot(
        id=facts.age_snapshot_id,
        child_profile_id=facts.child_id,
        as_of_date=date(2026, 10, 22),
        age_years=5,
        age_months=0,
        age_days=0,
        age_stage="3-6",
        age_rules_version="child-age-mvp-1",
        input_hash="a" * 64,
    )
    before = copy.deepcopy(manifest)
    with pytest.raises(ChildLineageMismatchError):
        compose_child_report_presentation(
            report=report,
            facts=facts,
            age_snapshot=age,
            segment_rows=[],
            generation_status="narrative_failed",
            current_local_date=date(2026, 10, 23),
        )
    assert report.presentation_manifest == before
