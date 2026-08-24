"""Contract tests for Astrotype v2 deterministic natal synthesis."""

from __future__ import annotations

import uuid
from pathlib import Path

from app.modules.astrotype_v2 import models

ROOT = Path(__file__).resolve().parents[3]


def _fact(
    *,
    chart_id: uuid.UUID,
    fact_type: str,
    fact_key: str,
    title: str,
    weight: float,
    section_hint: str | None,
    polarity: str | None = None,
    evidence_ids: list[str] | None = None,
) -> models.NatalFact:
    return models.NatalFact(
        chart_id=chart_id,
        fact_type=fact_type,
        fact_key=fact_key,
        title=title,
        summary=f"{title} summary",
        weight=weight,
        confidence=1.0,
        polarity=polarity,
        section_hint=section_hint,
        payload={"evidence_ids": evidence_ids or [f"evidence:{fact_key}"]},
        source_version="v2.0",
    )


def test_build_natal_synthesis_v2_groups_ranked_themes_without_llm_or_legacy_fields() -> None:
    from app.modules.astrotype_v2.synthesis import build_natal_synthesis_v2

    chart_id = uuid.uuid4()
    facts = [
        _fact(
            chart_id=chart_id,
            fact_type="placement",
            fact_key="placement:sun:aries:house_1",
            title="Sun in Aries, house 1",
            weight=0.92,
            section_hint="identity",
        ),
        _fact(
            chart_id=chart_id,
            fact_type="aspect",
            fact_key="aspect:moon:saturn:opposition",
            title="Moon opposition Saturn",
            weight=0.81,
            section_hint="emotional_regulation",
            polarity="tension",
        ),
        _fact(
            chart_id=chart_id,
            fact_type="balance",
            fact_key="balance:element:earth",
            title="Earth emphasis",
            weight=0.72,
            section_hint="agency",
            polarity="resource",
        ),
        _fact(
            chart_id=chart_id,
            fact_type="pattern",
            fact_key="pattern:angular_focus",
            title="Angular focus",
            weight=0.66,
            section_hint="growth",
            polarity="growth",
        ),
    ]

    synthesis = build_natal_synthesis_v2(chart_id=chart_id, facts=facts, source_version="v2.0")

    assert synthesis.contract_version == "natal_synthesis_v2"
    assert synthesis.chart_id == chart_id
    assert synthesis.source_version == "v2.0"
    assert [theme.id for theme in synthesis.dominant_themes] == [
        "theme:identity:placement:sun:aries:house_1",
        "theme:emotional_regulation:aspect:moon:saturn:opposition",
        "theme:agency:balance:element:earth",
        "theme:growth:pattern:angular_focus",
    ]
    assert [theme.primary_section for theme in synthesis.dominant_themes] == [
        "core_pattern",
        "emotional_regulation",
        "agency_and_desire",
        "growth_vector",
    ]
    assert synthesis.tensions[0].id == "theme:emotional_regulation:aspect:moon:saturn:opposition"
    assert synthesis.resources[0].id == "theme:agency:balance:element:earth"
    assert synthesis.growth_vectors[0].id == "theme:growth:pattern:angular_focus"
    assert synthesis.input_fact_keys == sorted(f.fact_key for f in facts)

    payload = synthesis.to_payload()
    assert payload["contract_version"] == "natal_synthesis_v2"
    assert payload["dominant_themes"][0]["evidence_ids"] == ["evidence:placement:sun:aries:house_1"]
    depth_theme = payload["dominant_themes"][0]
    assert depth_theme["psychological_mechanism"]
    assert depth_theme["lived_manifestation"]
    assert depth_theme["inner_tension"]
    assert depth_theme["protective_strategy"]
    assert depth_theme["immature_expression"]
    assert depth_theme["mature_expression"]
    assert depth_theme["integration_question"]
    assert depth_theme["evidence_strength"] == "strong"
    assert "socionics" not in str(payload).lower()
    assert "function_strength" not in str(payload).lower()
    assert "model_a" not in str(payload).lower()



def test_build_natal_synthesis_v2_preserves_explicit_depth_payload_evidence_backed() -> None:
    from app.modules.astrotype_v2.synthesis import build_natal_synthesis_v2

    chart_id = uuid.uuid4()
    fact = _fact(
        chart_id=chart_id,
        fact_type="placement",
        fact_key="placement:moon:cancer:house_4",
        title="Moon in Cancer, house 4",
        weight=0.86,
        section_hint="emotional_regulation",
        evidence_ids=["ev:moon"],
    )
    fact.payload["depth"] = {
        "psychological_mechanism": "explicit mechanism",
        "lived_manifestation": "explicit manifestation",
        "inner_tension": "explicit tension",
        "protective_strategy": "explicit protection",
        "immature_expression": "explicit immature",
        "mature_expression": "explicit mature",
        "integration_question": "explicit question?",
        "contradictions": ["need / fear"],
        "compensations": ["over-care"],
    }

    payload = build_natal_synthesis_v2(chart_id=chart_id, facts=[fact]).to_payload()
    theme = payload["dominant_themes"][0]

    assert theme["evidence_ids"] == ["ev:moon"]
    assert theme["psychological_mechanism"] == "explicit mechanism"
    assert theme["lived_manifestation"] == "explicit manifestation"
    assert theme["inner_tension"] == "explicit tension"
    assert theme["protective_strategy"] == "explicit protection"
    assert theme["immature_expression"] == "explicit immature"
    assert theme["mature_expression"] == "explicit mature"
    assert theme["integration_question"] == "explicit question?"
    assert theme["contradictions"] == ["need / fear"]
    assert theme["compensations"] == ["over-care"]

def test_build_natal_synthesis_v2_is_deterministic_for_same_fact_set_order_independent() -> None:
    from app.modules.astrotype_v2.synthesis import build_natal_synthesis_v2

    chart_id = uuid.uuid4()
    facts = [
        _fact(
            chart_id=chart_id,
            fact_type="balance",
            fact_key="balance:modality:fixed",
            title="Fixed modality emphasis",
            weight=0.4,
            section_hint="agency",
        ),
        _fact(
            chart_id=chart_id,
            fact_type="placement",
            fact_key="placement:venus:libra:house_7",
            title="Venus in Libra, house 7",
            weight=0.7,
            section_hint="relationships",
        ),
    ]

    first = build_natal_synthesis_v2(chart_id=chart_id, facts=facts, source_version="v2.0")
    second = build_natal_synthesis_v2(chart_id=chart_id, facts=list(reversed(facts)), source_version="v2.0")

    assert first.to_payload() == second.to_payload()


def test_synthesis_module_does_not_import_legacy_socionics_or_report_narratives() -> None:
    synthesis_path = ROOT / "app" / "modules" / "astrotype_v2" / "synthesis.py"
    source = synthesis_path.read_text()

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
