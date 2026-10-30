"""Versioned citation authority: providers cite claims, application derives the list."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from tests.unit.test_child.test_content_v2 import _middle_facts
from tests.unit.test_child.test_content_v3 import _frozen_facts

from app.modules.child.assembly import assemble_child_report_payload
from app.modules.child.narrative import (
    ChildSectionRenderInput,
    MockChildSegmentProvider,
    _stable_hash,
    build_child_section_inputs,
    run_child_segment_generation,
)
from app.modules.child.prompts.v1 import build_child_section_prompt

V4 = "child-section-prompt-v4"


@pytest.mark.asyncio
async def test_v4_provider_omits_redundant_list_application_persists_derived_citations() -> None:
    facts = _middle_facts(contract_version="child-guidance-facts-v3")
    old_inputs = build_child_section_inputs(facts)
    inputs = build_child_section_inputs(facts, prompt_version=V4)
    assert all(item.contract_version == "child_section_render_input_v4" for item in inputs)
    for old, item in zip(old_inputs, inputs, strict=True):
        assert old.owned_facts == item.owned_facts
        assert _stable_hash(old.model_dump(mode="json")) != _stable_hash(item.model_dump(mode="json"))
        prompt = build_child_section_prompt(item)
        assert "whole approved_text" in prompt and "multiple sentences" in prompt
        assert "Do not split" in prompt
        assert "sentence copied from body" not in prompt
        if not item.owned_facts:
            continue
        raw = await MockChildSegmentProvider().generate_segment(prompt=prompt, section_input=item)
        assert raw["contract_version"] == "child_segment_output_v2"
        assert "cited_fact_ids" not in raw
    rows = [
        await run_child_segment_generation(
            provider=MockChildSegmentProvider(), section_input=item, guidance_facts=facts
        )
        for item in inputs
    ]
    assert all(row.status in {"ready", "not_applicable"} for row in rows)
    for row in rows:
        if row.status == "ready":
            output = row.diagnostics["output"]
            assert output["cited_fact_ids"] == [claim["fact_ids"][0] for claim in output["claims"]]
    assembly = assemble_child_report_payload(guidance_facts=facts, segment_rows=rows, prompt_version=V4)
    assert assembly["contract_version"] == "child_report_narrative_v4"
    assert assembly["prompt_version"] == V4


@pytest.mark.asyncio
async def test_v3_inputs_prompt_hashes_outputs_and_assembly_remain_frozen() -> None:
    fixture = json.loads((Path(__file__).parent / "fixtures/content_v3_frozen.json").read_text())
    facts = _frozen_facts(fixture)
    inputs = build_child_section_inputs(facts)
    assert [item.model_dump(mode="json") for item in inputs] == fixture["inputs"]
    assert [_stable_hash({"prompt": build_child_section_prompt(item)}) for item in inputs] == fixture["prompt_hashes"]
    rows = [
        await run_child_segment_generation(
            provider=MockChildSegmentProvider(), section_input=item, guidance_facts=facts
        )
        for item in inputs
    ]
    assert all("cited_fact_ids" in row.diagnostics["output"] for row in rows if row.status == "ready")
    assert (
        _stable_hash(assemble_child_report_payload(guidance_facts=facts, segment_rows=rows)) == fixture["assembly_hash"]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutation,reason",
    [
        ("redundant_list", "output_schema"),
        ("duplicate", "citation_mismatch"),
        ("fragment", "claim_rendering_mismatch"),
        ("split_fragments", "citation_mismatch"),
        ("missing_owned", "missing_owned_facts"),
        ("unknown", "unsupported_facts"),
        ("missing_id", "output_schema"),
        ("two_ids", "output_schema"),
        ("unhashable_id", "output_schema"),
        ("conditional", "claim_rendering_mismatch"),
        ("conditional_coercion", "output_schema"),
        ("body", "body_claim_mismatch"),
        ("title", "section_mismatch"),
        ("section", "section_mismatch"),
        ("wrong_version", "output_schema"),
    ],
)
async def test_v4_rejects_adversarial_outputs_without_persisting_provider_text(mutation: str, reason: str) -> None:
    from copy import deepcopy

    facts = _middle_facts(contract_version="child-guidance-facts-v3")
    section = next(item for item in build_child_section_inputs(facts, prompt_version=V4) if len(item.owned_facts) > 1)
    assert any(fact.approved_text.count(".") > 1 for fact in section.owned_facts)
    raw = await MockChildSegmentProvider().generate_segment(prompt="", section_input=section)
    if mutation == "redundant_list":
        raw["cited_fact_ids"] = [claim["fact_ids"][0] for claim in raw["claims"]]
    elif mutation == "duplicate":
        raw["claims"].append(deepcopy(raw["claims"][0]))
    elif mutation == "fragment":
        raw["claims"][0]["text"] = raw["claims"][0]["text"].split(".")[0] + "."
    elif mutation == "split_fragments":
        claim = raw["claims"].pop(0)
        raw["claims"] = [{**claim, "text": sentence + "."} for sentence in claim["text"].split(".") if sentence] + raw[
            "claims"
        ]
    elif mutation == "missing_owned":
        raw["claims"].pop()
    elif mutation == "unknown":
        raw["claims"][0]["fact_ids"] = ["unknown-private-id"]
    elif mutation in {"missing_id", "two_ids", "unhashable_id"}:
        raw["claims"][0]["fact_ids"] = {
            "missing_id": [],
            "two_ids": ["owned-1", "owned-2"],
            "unhashable_id": [["owned-1"]],
        }[mutation]
    elif mutation == "conditional":
        raw["claims"][0]["conditional"] = not raw["claims"][0]["conditional"]
    elif mutation == "conditional_coercion":
        raw["claims"][0]["conditional"] = str(raw["claims"][0]["conditional"]).lower()
    elif mutation == "title":
        raw["title"] = "changed"
    elif mutation == "section":
        raw["section_key"] = "praise_recognition"
    elif mutation == "wrong_version":
        raw["contract_version"] = "child_segment_output_v1"
    raw["body"] = " ".join(claim["text"] for claim in raw["claims"])
    if mutation == "body":
        raw["body"] += " unapproved addition"
    before = deepcopy(raw)

    class AdversarialProvider(MockChildSegmentProvider):
        async def generate_segment(self, *, prompt: str, section_input: ChildSectionRenderInput) -> dict[str, Any]:
            return raw

    row = await run_child_segment_generation(
        provider=AdversarialProvider(), section_input=section, guidance_facts=facts
    )
    assert raw == before
    assert row.status == "failed" and row.error_code == "child_narrative_validation_failure"
    assert row.diagnostics["validation_reason"] == reason
    assert row.content is None and row.evidence_refs == []
    assert "output" not in row.diagnostics and "output_hash" not in row.diagnostics


@pytest.mark.asyncio
async def test_v4_stored_derived_list_is_verified_not_repaired_and_claim_order_preserved() -> None:
    from app.modules.child.narrative import ChildNarrativeValidationError

    facts = _middle_facts(contract_version="child-guidance-facts-v3")
    section = next(item for item in build_child_section_inputs(facts, prompt_version=V4) if len(item.owned_facts) > 1)

    class ReverseProvider(MockChildSegmentProvider):
        async def generate_segment(self, *, prompt: str, section_input: ChildSectionRenderInput) -> dict[str, Any]:
            raw = await super().generate_segment(prompt=prompt, section_input=section_input)
            raw["claims"].reverse()
            raw["body"] = " ".join(claim["text"] for claim in raw["claims"])
            return raw

    row = await run_child_segment_generation(provider=ReverseProvider(), section_input=section, guidance_facts=facts)
    assert row.status == "ready"
    assert row.diagnostics["output"]["cited_fact_ids"] == list(reversed(section.owned_fact_ids))
    row.diagnostics["output"]["cited_fact_ids"].reverse()
    row.diagnostics["output_hash"] = _stable_hash(row.diagnostics["output"])
    with pytest.raises(ChildNarrativeValidationError, match="claims and cited"):
        assemble_child_report_payload(guidance_facts=facts, segment_rows=[row], prompt_version=V4)


@pytest.mark.asyncio
async def test_v4_structured_adapter_sends_provider_schema_without_derived_field() -> None:
    from app.modules.child.narrative import (
        ChildProviderOutputV2,
        ChildSegmentOutput,
        StructuredChildSegmentProviderAdapter,
    )

    facts = _middle_facts(contract_version="child-guidance-facts-v3")
    section = build_child_section_inputs(facts, prompt_version=V4)[0]

    class StructuredProvider:
        async def generate_structured(
            self, *, prompt: str, narrative_input: Any, schema: type[ChildSegmentOutput] | type[ChildProviderOutputV2]
        ) -> ChildSegmentOutput | ChildProviderOutputV2:
            assert schema is ChildProviderOutputV2
            assert "cited_fact_ids" not in schema.model_fields
            raw = await MockChildSegmentProvider().generate_segment(prompt=prompt, section_input=narrative_input)
            return schema.model_validate(raw)

    row = await run_child_segment_generation(
        provider=StructuredChildSegmentProviderAdapter(
            provider=StructuredProvider(), provider_name="mock", model_name="offline-v4"
        ),
        section_input=section,
        guidance_facts=facts,
    )
    assert row.status == "ready" and row.diagnostics["output"]["cited_fact_ids"]


@pytest.mark.asyncio
async def test_v4_preserves_safety_gate_and_rejects_forged_input_and_row_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from uuid import uuid4

    from app.modules.child.narrative import ChildNarrativeValidationError
    from app.modules.child.safety import ChildSafetyViolation

    facts = _middle_facts(contract_version="child-guidance-facts-v3")
    section = build_child_section_inputs(facts, prompt_version=V4)[0]
    forged = section.model_copy(
        update={"owned_facts": [section.owned_facts[0].model_copy(update={"approved_text": "unapproved"})]}
    )
    with pytest.raises(ChildNarrativeValidationError, match="not canonical"):
        await run_child_segment_generation(
            provider=MockChildSegmentProvider(), section_input=forged, guidance_facts=facts
        )
    row = await run_child_segment_generation(
        provider=MockChildSegmentProvider(), section_input=section, guidance_facts=facts
    )
    row.child_profile_id = uuid4()
    with pytest.raises(ChildNarrativeValidationError, match="lineage"):
        assemble_child_report_payload(guidance_facts=facts, segment_rows=[row], prompt_version=V4)

    def reject_safety(*args: Any, **kwargs: Any) -> None:
        raise ChildSafetyViolation(("section_fact_ownership",))

    monkeypatch.setattr("app.modules.child.narrative.validate_child_narrative", reject_safety)
    rejected = await run_child_segment_generation(
        provider=MockChildSegmentProvider(), section_input=section, guidance_facts=facts
    )
    assert rejected.status == "failed" and rejected.diagnostics["validation_reason"] == "safety_validation"
    assert rejected.content is None and rejected.evidence_refs == [] and "output" not in rejected.diagnostics


@pytest.mark.parametrize("facts_version", ["child-guidance-facts-v1", "child-guidance-facts-v2"])
def test_v4_cannot_be_selected_for_historical_fact_policy(facts_version: str) -> None:
    from tests.unit.test_child.test_narrative_pipeline import _facts

    from app.modules.child.narrative import ChildNarrativeValidationError

    facts = _facts() if facts_version.endswith("v1") else _middle_facts()
    with pytest.raises(ChildNarrativeValidationError, match="prompt version"):
        build_child_section_inputs(facts, prompt_version=V4)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "facts_version", ["child-guidance-facts-v1", "child-guidance-facts-v2", "child-guidance-facts-v3"]
)
async def test_accepted_legacy_output_is_returned_unchanged_not_deduplicated(facts_version: str) -> None:
    from copy import deepcopy

    from tests.unit.test_child.test_narrative_pipeline import _facts

    from app.modules.child.narrative import ChildSegmentOutput, validate_segment_output

    facts = _facts() if facts_version.endswith("v1") else _middle_facts(contract_version=facts_version)
    section = next(item for item in build_child_section_inputs(facts) if item.owned_facts)
    raw = await MockChildSegmentProvider().generate_segment(prompt="", section_input=section)
    parsed = ChildSegmentOutput.model_validate(raw)
    snapshot = deepcopy(parsed.model_dump(mode="json"))
    validated = validate_segment_output(output=parsed, section_input=section, guidance_facts=facts)
    assert validated is parsed
    assert validated.model_dump(mode="json") == snapshot == raw
