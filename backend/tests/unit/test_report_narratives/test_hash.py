"""Unit tests for NarrativeInput hashing stability."""

from __future__ import annotations

from typing import Any, cast

from tests.unit.test_report_narratives.test_schemas import make_narrative_input_payload

from app.modules.report_narratives.hash import compute_input_hash
from app.modules.report_narratives.schemas import NarrativeInput


def test_compute_input_hash_is_stable_for_semantically_identical_payloads() -> None:
    payload_a = make_narrative_input_payload()
    payload_b = make_narrative_input_payload()

    key_facts = cast(list[dict[str, Any]], payload_b["key_facts"])
    product_boundaries = cast(dict[str, Any], payload_b["product_boundaries"])
    allowed_sections = cast(list[str], product_boundaries["allowed_sections"])

    payload_b["key_facts"] = list(reversed(key_facts))
    product_boundaries["allowed_sections"] = list(reversed(allowed_sections))

    hash_a = compute_input_hash(NarrativeInput.model_validate(payload_a))
    hash_b = compute_input_hash(NarrativeInput.model_validate(payload_b))

    assert hash_a == hash_b


def test_compute_input_hash_changes_when_meaningful_content_changes() -> None:
    payload_a = make_narrative_input_payload()
    payload_b = make_narrative_input_payload()
    strengths = cast(list[dict[str, Any]], payload_b["strengths"])
    strengths[0]["claim"] = "Вы заражаете идеей ещё сильнее."

    hash_a = compute_input_hash(NarrativeInput.model_validate(payload_a))
    hash_b = compute_input_hash(NarrativeInput.model_validate(payload_b))

    assert hash_a != hash_b
