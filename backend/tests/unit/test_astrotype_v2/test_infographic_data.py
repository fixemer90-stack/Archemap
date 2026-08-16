"""Contract tests for Astrotype v2 infographic calculation-layer payloads."""

from __future__ import annotations

import uuid
from pathlib import Path

from app.modules.astrotype_v2 import models

ROOT = Path(__file__).resolve().parents[3]


def _chart_id() -> uuid.UUID:
    return uuid.uuid4()


def _positions(chart_id: uuid.UUID) -> list[models.NatalPlanetPosition]:
    return [
        models.NatalPlanetPosition(
            chart_id=chart_id,
            body="Sun",
            longitude=12.5,
            latitude=0.0,
            speed=1.0,
            sign="Aries",
            sign_degree=12.5,
            house_number=1,
            retrograde=False,
        ),
        models.NatalPlanetPosition(
            chart_id=chart_id,
            body="Moon",
            longitude=186.25,
            latitude=1.1,
            speed=13.0,
            sign="Libra",
            sign_degree=6.25,
            house_number=7,
            retrograde=False,
        ),
        models.NatalPlanetPosition(
            chart_id=chart_id,
            body="Ascendant",
            longitude=1.0,
            latitude=None,
            speed=None,
            sign="Aries",
            sign_degree=1.0,
            house_number=1,
            retrograde=False,
        ),
    ]


def _houses(chart_id: uuid.UUID) -> list[models.NatalHouse]:
    return [
        models.NatalHouse(chart_id=chart_id, house_number=1, longitude=1.0, sign="Aries"),
        models.NatalHouse(chart_id=chart_id, house_number=7, longitude=181.0, sign="Libra"),
    ]


def _aspects(chart_id: uuid.UUID) -> list[models.NatalAspect]:
    return [
        models.NatalAspect(
            chart_id=chart_id,
            body_a="Sun",
            body_b="Moon",
            aspect_code="opposition",
            angle_degrees=180.0,
            orb_degrees=3.75,
            applying=True,
            strength=0.82,
        )
    ]


def _balances(chart_id: uuid.UUID) -> list[models.NatalChartBalance]:
    return [
        models.NatalChartBalance(chart_id=chart_id, category="element", key="fire", value=0.6, rank=1),
        models.NatalChartBalance(chart_id=chart_id, category="element", key="air", value=0.4, rank=2),
        models.NatalChartBalance(chart_id=chart_id, category="modality", key="cardinal", value=1.0, rank=1),
    ]


def _facts(chart_id: uuid.UUID) -> list[models.NatalFact]:
    return [
        models.NatalFact(
            chart_id=chart_id,
            fact_type="placement",
            fact_key="placement:sun:aries:house_1",
            title="Sun in Aries, house 1",
            summary="Sun is in Aries in the first house.",
            weight=1.0,
            confidence=1.0,
            polarity=None,
            section_hint="core_pattern",
            payload={"body": "Sun", "sign": "Aries", "house_number": 1},
            source_version="v2.0",
        ),
        models.NatalFact(
            chart_id=chart_id,
            fact_type="aspect",
            fact_key="aspect:sun:moon:opposition",
            title="Sun opposition Moon",
            summary="Sun and Moon form an opposition.",
            weight=0.82,
            confidence=1.0,
            polarity="tension",
            section_hint="emotional_regulation",
            payload={"body_a": "Sun", "body_b": "Moon", "aspect_code": "opposition"},
            source_version="v2.0",
        ),
    ]


def _evidence(chart_id: uuid.UUID, facts: list[models.NatalFact]) -> list[models.NatalFactEvidence]:
    return [
        models.NatalFactEvidence(
            fact_id=facts[0].id,
            chart_id=chart_id,
            source_table="astrotype_v2_natal_planet_positions",
            source_id=uuid.uuid4(),
            source_key="planet_position:Sun",
            payload={"body": "Sun"},
        ),
        models.NatalFactEvidence(
            fact_id=facts[1].id,
            chart_id=chart_id,
            source_table="astrotype_v2_natal_aspects",
            source_id=uuid.uuid4(),
            source_key="aspect:Sun:Moon:opposition",
            payload={"aspect_code": "opposition"},
        ),
    ]


def test_build_natal_infographic_data_v2_matches_canonical_lower_layer_blocks() -> None:
    from app.modules.astrotype_v2.infographic_data import build_natal_infographic_data_v2

    chart_id = _chart_id()
    payload = build_natal_infographic_data_v2(
        chart_id=chart_id,
        positions=_positions(chart_id),
        houses=_houses(chart_id),
        aspects=_aspects(chart_id),
        balances=_balances(chart_id),
        facts=_facts(chart_id),
        evidence=[],
    )

    assert payload["contract_version"] == "natal_infographic_data_v2"
    assert payload["chart_id"] == str(chart_id)
    assert set(payload) >= {
        "key_indicators",
        "planet_positions",
        "balance_bars",
        "house_accents",
        "aspect_network",
        "aspect_table",
        "calculation_matrix",
        "evidence_cards",
        "progressive_disclosure",
    }
    assert payload["key_indicators"]["ascendant"]["sign"] == "Aries"
    assert payload["key_indicators"]["sun"]["sign"] == "Aries"
    assert payload["key_indicators"]["moon"]["sign"] == "Libra"
    assert payload["planet_positions"][0]["body"] == "Sun"
    assert payload["planet_positions"][0]["degree_label"] == "12.50° Aries"
    assert payload["reader_blocks"] == [
        "key_indicators",
        "planet_positions",
        "balance_bars",
        "house_emphasis",
        "aspect_network",
        "key_aspects",
        "calculation_matrix",
    ]
    assert payload["planet_positions"][0]["sampled_aspects"][0]["body_b"] == "Moon"
    assert payload["balance_bars"]["element"][0] == {"category": "element", "key": "fire", "value": 0.6, "rank": 1}
    assert payload["house_emphasis"]["bars"][0]["house_number"] == 1
    assert payload["house_emphasis"]["top_houses"][0]["body_count"] > 0
    assert payload["aspect_network"]["edges"][0]["source"] == "Sun"
    assert payload["aspect_network"]["edges"][0]["target"] == "Moon"
    assert payload["aspect_table"][0]["orb_degrees"] == 3.75
    assert payload["key_aspects"][0]["orb_degrees"] == 3.75
    assert payload["calculation_matrix"]["counts"] == {"positions": 3, "houses": 2, "aspects": 1, "facts": 2}
    assert set(payload["calculation_matrix"]) >= {"house_mode", "hemispheres", "quadrants", "aspect_profile"}

    forbidden = ("archetype", "theme_map", "factual_basis_dashboard", "most_aspected", "socionics", "model_a")
    payload_text = str(payload).lower()
    for fragment in forbidden:
        assert fragment not in payload_text


def test_build_evidence_cards_v2_compactly_links_facts_to_sources_and_sections() -> None:
    from app.modules.astrotype_v2.infographic_data import build_evidence_cards_v2

    chart_id = _chart_id()
    facts = _facts(chart_id)
    evidence = _evidence(chart_id, facts)

    cards = build_evidence_cards_v2(facts=facts, evidence=evidence)

    assert [card["fact_key"] for card in cards] == ["placement:sun:aries:house_1", "aspect:sun:moon:opposition"]
    assert cards[0]["section_usage"] == ["core_pattern"]
    assert cards[0]["technical_value"] == {"body": "Sun", "sign": "Aries", "house_number": 1}
    assert cards[0]["sources"][0]["source_table"] == "astrotype_v2_natal_planet_positions"
    assert cards[1]["badge"] == "tension"


def test_build_infographic_api_payload_v2_is_client_reusable_and_llm_free() -> None:
    from app.modules.astrotype_v2.infographic_data import build_evidence_cards_v2, build_infographic_api_payload_v2

    chart_id = _chart_id()
    facts = _facts(chart_id)
    payload = build_infographic_api_payload_v2(
        chart_id=chart_id,
        source_version="v2.0",
        calculation_layer={"contract_version": "natal_infographic_data_v2", "planet_positions": []},
        evidence_cards=build_evidence_cards_v2(facts=facts, evidence=[]),
    )

    assert payload == {
        "contract_version": "natal_infographic_api_v2",
        "chart_id": str(chart_id),
        "source_version": "v2.0",
        "calculation_layer": {"contract_version": "natal_infographic_data_v2", "planet_positions": []},
        "evidence_cards": [
            {
                "fact_key": "placement:sun:aries:house_1",
                "title": "Sun in Aries, house 1",
                "summary": "Sun is in Aries in the first house.",
                "fact_type": "placement",
                "section_usage": ["core_pattern"],
                "technical_value": {"body": "Sun", "sign": "Aries", "house_number": 1},
                "weight": 1.0,
                "confidence": 1.0,
                "badge": "placement",
                "sources": [],
            },
            {
                "fact_key": "aspect:sun:moon:opposition",
                "title": "Sun opposition Moon",
                "summary": "Sun and Moon form an opposition.",
                "fact_type": "aspect",
                "section_usage": ["emotional_regulation"],
                "technical_value": {"body_a": "Sun", "body_b": "Moon", "aspect_code": "opposition"},
                "weight": 0.82,
                "confidence": 1.0,
                "badge": "tension",
                "sources": [],
            },
        ],
    }


def test_build_natal_infographic_data_row_uses_v2_model_without_side_effects() -> None:
    from app.modules.astrotype_v2.infographic_data import build_natal_infographic_data_row

    chart_id = _chart_id()
    row = build_natal_infographic_data_row(
        chart_id=chart_id,
        positions=_positions(chart_id),
        houses=_houses(chart_id),
        aspects=_aspects(chart_id),
        balances=_balances(chart_id),
        facts=_facts(chart_id),
        evidence=[],
        source_version="v2.0",
    )

    assert row.chart_id == chart_id
    assert row.status == "ready"
    assert row.source_version == "v2.0"
    assert row.calculation_layer["contract_version"] == "natal_infographic_data_v2"


def test_infographic_data_source_is_legacy_isolated_and_does_not_use_llm_or_deferred_blocks() -> None:
    source = (ROOT / "app" / "modules" / "astrotype_v2" / "infographic_data.py").read_text()
    forbidden = (
        "report_narratives",
        "socionics",
        "model_a",
        "provider",
        "generate_segment",
        "openai",
        "archetype",
        "theme_map",
        "most_aspected",
    )
    for fragment in forbidden:
        assert fragment not in source
