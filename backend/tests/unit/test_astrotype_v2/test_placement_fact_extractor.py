"""Contract tests for Astrotype v2 placement fact extraction."""

from __future__ import annotations

import uuid
from pathlib import Path

from app.modules.astrotype_v2 import models

ROOT = Path(__file__).resolve().parents[3]

FORBIDDEN_EXTRACTOR_FRAGMENTS = (
    "socionics",
    "function_strength",
    "model_a",
    "report_narrative",
    "chart_snapshots",
    "ChartSnapshot",
)


def _position(*, chart_id: uuid.UUID, body: str = "Mars") -> models.NatalPlanetPosition:
    return models.NatalPlanetPosition(
        chart_id=chart_id,
        body=body,
        longitude=45.25,
        latitude=0.1,
        speed=-0.24,
        sign="Taurus",
        sign_degree=15.25,
        house_number=10,
        retrograde=True,
    )


def test_build_placement_fact_rows_creates_fact_and_v2_evidence_for_each_position() -> None:
    from app.modules.astrotype_v2.fact_extractor import build_placement_fact_rows

    chart_id = uuid.uuid4()
    position = _position(chart_id=chart_id)

    facts, evidence = build_placement_fact_rows(chart_id=chart_id, positions=[position], source_version="v2.0")

    assert len(facts) == 1
    assert len(evidence) == 1

    fact = facts[0]
    assert isinstance(fact, models.NatalFact)
    assert fact.chart_id == chart_id
    assert fact.fact_type == "placement"
    assert fact.fact_key == "placement:mars:taurus:house_10"
    assert fact.title == "Mars in Taurus, house 10"
    assert fact.summary == "Mars is in Taurus in house 10."
    assert fact.weight == 1.0
    assert fact.confidence == 1.0
    assert fact.polarity is None
    assert fact.section_hint == "placements"
    assert fact.source_version == "v2.0"
    assert fact.payload == {
        "body": "Mars",
        "sign": "Taurus",
        "sign_degree": 15.25,
        "house_number": 10,
        "retrograde": True,
        "longitude": 45.25,
    }

    link = evidence[0]
    assert isinstance(link, models.NatalFactEvidence)
    assert link.fact_id == fact.id
    assert link.chart_id == chart_id
    assert link.source_table == "astrotype_v2_natal_planet_positions"
    assert link.source_id == position.id
    assert link.source_key == "planet_position:Mars"
    assert link.payload == {"body": "Mars", "fact_key": "placement:mars:taurus:house_10"}


def test_build_placement_fact_rows_uses_stable_key_without_house_when_missing() -> None:
    from app.modules.astrotype_v2.fact_extractor import build_placement_fact_rows

    chart_id = uuid.uuid4()
    position = _position(chart_id=chart_id, body="Moon")
    position.house_number = None
    position.retrograde = False

    facts, evidence = build_placement_fact_rows(chart_id=chart_id, positions=[position], source_version="v2.0")

    assert facts[0].fact_key == "placement:moon:taurus:no_house"
    assert facts[0].title == "Moon in Taurus"
    assert facts[0].summary == "Moon is in Taurus."
    assert facts[0].payload["house_number"] is None
    assert evidence[0].source_key == "planet_position:Moon"


def test_fact_extractor_source_is_side_effect_free_and_legacy_isolated() -> None:
    extractor_path = ROOT / "app" / "modules" / "astrotype_v2" / "fact_extractor.py"
    extractor_text = extractor_path.read_text()

    assert "session" not in extractor_text
    assert "commit" not in extractor_text
    assert "flush" not in extractor_text
    for fragment in FORBIDDEN_EXTRACTOR_FRAGMENTS:
        assert fragment not in extractor_text
