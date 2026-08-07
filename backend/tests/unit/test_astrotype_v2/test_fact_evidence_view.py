"""Contract tests for Astrotype v2 fact evidence API payload shape."""

from __future__ import annotations

import uuid
from pathlib import Path

from app.modules.astrotype_v2 import models

ROOT = Path(__file__).resolve().parents[3]

FORBIDDEN_VIEW_FRAGMENTS = (
    "socionics",
    "function_strength",
    "model_a",
    "report_narrative",
    "chart_snapshots",
    "ChartSnapshot",
)


def test_build_fact_evidence_payload_groups_evidence_under_serializable_facts() -> None:
    from app.modules.astrotype_v2.fact_view import build_fact_evidence_payload

    chart_id = uuid.uuid4()
    fact = models.NatalFact(
        chart_id=chart_id,
        fact_type="placement",
        fact_key="placement:mars:taurus:house_10",
        title="Mars in Taurus, house 10",
        summary="Mars is in Taurus in house 10.",
        weight=1.0,
        confidence=1.0,
        polarity=None,
        section_hint="placements",
        payload={"body": "Mars"},
        source_version="v2.0",
    )
    evidence = models.NatalFactEvidence(
        fact_id=fact.id,
        chart_id=chart_id,
        source_table="astrotype_v2_natal_planet_positions",
        source_id=uuid.uuid4(),
        source_key="planet_position:Mars",
        payload={"fact_key": fact.fact_key},
    )

    payload = build_fact_evidence_payload(facts=[fact], evidence=[evidence])

    assert payload == [
        {
            "id": str(fact.id),
            "chart_id": str(chart_id),
            "fact_type": "placement",
            "fact_key": "placement:mars:taurus:house_10",
            "title": "Mars in Taurus, house 10",
            "summary": "Mars is in Taurus in house 10.",
            "weight": 1.0,
            "confidence": 1.0,
            "polarity": None,
            "section_hint": "placements",
            "payload": {"body": "Mars"},
            "source_version": "v2.0",
            "evidence": [
                {
                    "id": str(evidence.id),
                    "source_table": "astrotype_v2_natal_planet_positions",
                    "source_id": str(evidence.source_id),
                    "source_key": "planet_position:Mars",
                    "payload": {"fact_key": fact.fact_key},
                }
            ],
        }
    ]


def test_build_fact_evidence_payload_rejects_non_v2_evidence_sources() -> None:
    from app.modules.astrotype_v2.fact_view import build_fact_evidence_payload

    chart_id = uuid.uuid4()
    fact = models.NatalFact(
        chart_id=chart_id,
        fact_type="placement",
        fact_key="placement:sun:leo:house_1",
        title="Sun in Leo, house 1",
        summary="Sun is in Leo in house 1.",
        weight=1.0,
        confidence=1.0,
        payload={},
        source_version="v2.0",
    )
    evidence = models.NatalFactEvidence(
        fact_id=fact.id,
        chart_id=chart_id,
        source_table="chart_snapshots",
        source_id=uuid.uuid4(),
        source_key="legacy",
        payload={},
    )

    try:
        build_fact_evidence_payload(facts=[fact], evidence=[evidence])
    except ValueError as exc:
        assert "non-v2 evidence source" in str(exc)
    else:
        raise AssertionError("legacy evidence source was accepted")


def test_fact_view_source_is_legacy_isolated_and_side_effect_free() -> None:
    view_path = ROOT / "app" / "modules" / "astrotype_v2" / "fact_view.py"
    view_text = view_path.read_text()

    assert "commit" not in view_text
    assert "flush" not in view_text
    for fragment in FORBIDDEN_VIEW_FRAGMENTS:
        assert fragment not in view_text
