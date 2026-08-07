"""Contract tests for Astrotype v2 balance and pattern fact extraction."""

from __future__ import annotations

import uuid

from app.modules.astrotype_v2 import models


def test_build_balance_pattern_fact_rows_extracts_balance_and_pattern_facts_with_v2_evidence() -> None:
    from app.modules.astrotype_v2.fact_extractor import build_balance_pattern_fact_rows

    chart_id = uuid.uuid4()
    balance = models.NatalChartBalance(
        chart_id=chart_id,
        category="element",
        key="earth",
        value=0.6,
        rank=1,
    )
    pattern = models.NatalChartPattern(
        chart_id=chart_id,
        pattern_code="emphasis_element_earth",
        label="element emphasis: earth",
        weight=0.6,
        evidence={"category": "element", "key": "earth", "value": 0.6},
    )

    facts, evidence = build_balance_pattern_fact_rows(
        chart_id=chart_id,
        balances=[balance],
        patterns=[pattern],
        source_version="v2.0",
    )

    assert len(facts) == 2
    assert len(evidence) == 2

    balance_fact = facts[0]
    assert balance_fact.fact_type == "balance"
    assert balance_fact.fact_key == "balance:element:earth"
    assert balance_fact.title == "element balance: earth"
    assert balance_fact.summary == "earth is the #1 element balance at 0.6."
    assert balance_fact.weight == 0.6
    assert balance_fact.confidence == 1.0
    assert balance_fact.section_hint == "balances"
    assert balance_fact.payload == {"category": "element", "key": "earth", "value": 0.6, "rank": 1}

    pattern_fact = facts[1]
    assert pattern_fact.fact_type == "pattern"
    assert pattern_fact.fact_key == "pattern:emphasis_element_earth"
    assert pattern_fact.title == "element emphasis: earth"
    assert pattern_fact.summary == "Detected pattern: element emphasis: earth."
    assert pattern_fact.weight == 0.6
    assert pattern_fact.confidence == 1.0
    assert pattern_fact.section_hint == "patterns"
    assert pattern_fact.payload == {
        "pattern_code": "emphasis_element_earth",
        "label": "element emphasis: earth",
        "weight": 0.6,
        "evidence": {"category": "element", "key": "earth", "value": 0.6},
    }

    assert evidence[0].fact_id == balance_fact.id
    assert evidence[0].source_table == "astrotype_v2_natal_chart_balances"
    assert evidence[0].source_id == balance.id
    assert evidence[0].source_key == "balance:element:earth"
    assert evidence[0].payload == {"fact_key": "balance:element:earth"}

    assert evidence[1].fact_id == pattern_fact.id
    assert evidence[1].source_table == "astrotype_v2_natal_chart_patterns"
    assert evidence[1].source_id == pattern.id
    assert evidence[1].source_key == "pattern:emphasis_element_earth"
    assert evidence[1].payload == {"fact_key": "pattern:emphasis_element_earth"}


def test_build_balance_pattern_fact_rows_handles_missing_rank_and_weight() -> None:
    from app.modules.astrotype_v2.fact_extractor import build_balance_pattern_fact_rows

    chart_id = uuid.uuid4()
    balance = models.NatalChartBalance(chart_id=chart_id, category="house", key="10", value=0.25, rank=None)
    pattern = models.NatalChartPattern(
        chart_id=chart_id,
        pattern_code="angular_focus",
        label="Angular focus",
        weight=None,
        evidence={},
    )

    facts, _ = build_balance_pattern_fact_rows(
        chart_id=chart_id,
        balances=[balance],
        patterns=[pattern],
        source_version="v2.0",
    )

    assert facts[0].fact_key == "balance:house:10"
    assert facts[0].summary == "10 is a house balance at 0.25."
    assert facts[1].weight == 0.0
