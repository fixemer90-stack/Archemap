"""Offline BUG50 diagnostics: reconstructed failures, never provider-response replay."""

from __future__ import annotations

from typing import Any

import pytest
from tests.unit.test_child.test_content_v2 import _middle_facts

from app.modules.child.assembly import assemble_child_report_payload
from app.modules.child.narrative import (
    ChildNarrativeValidationError,
    ChildSectionRenderInput,
    MockChildSegmentProvider,
    build_child_section_inputs,
    run_child_segment_generation,
)


@pytest.mark.asyncio
async def test_v3_rejected_praise_preserves_bounded_reason_without_response_text() -> None:
    facts = _middle_facts(contract_version="child-guidance-facts-v3")
    section = next(item for item in build_child_section_inputs(facts) if item.section_key == "praise_recognition")

    class ChangedClaimProvider(MockChildSegmentProvider):
        calls = 0

        async def generate_segment(self, *, prompt: str, section_input: ChildSectionRenderInput) -> dict[str, Any]:
            self.calls += 1
            output = await super().generate_segment(prompt=prompt, section_input=section_input)
            output["claims"][0]["text"] = "PRIVATE rejected response must not be retained"
            return output

    provider = ChangedClaimProvider()
    row = await run_child_segment_generation(provider=provider, section_input=section, guidance_facts=facts)
    assert row.status == "failed"
    assert row.error_code == "child_narrative_validation_failure"
    assert row.diagnostics["validation_reason"] == "claim_rendering_mismatch"
    assert row.content is None and row.evidence_refs == []
    assert "output" not in row.diagnostics and "output_hash" not in row.diagnostics
    assert "PRIVATE" not in str(row.diagnostics)
    assert row.diagnostics["attempts"] == provider.calls == 1
    assembly = assemble_child_report_payload(guidance_facts=facts, segment_rows=[row])
    assert assembly["failed_sections"] == ["praise_recognition"]
    assert "validation_reason" not in str(assembly)


@pytest.mark.asyncio
async def test_v3_unknown_validation_exception_uses_non_sensitive_fallback() -> None:
    facts = _middle_facts(contract_version="child-guidance-facts-v3")

    class PrivateErrorProvider(MockChildSegmentProvider):
        async def generate_segment(self, *, prompt: str, section_input: ChildSectionRenderInput) -> dict[str, Any]:
            raise ChildNarrativeValidationError("PRIVATE provider data")

    row = await run_child_segment_generation(
        provider=PrivateErrorProvider(), section_input=build_child_section_inputs(facts)[0], guidance_facts=facts
    )
    assert row.diagnostics["validation_reason"] == "contract_validation"
    assert "PRIVATE" not in str(row.diagnostics)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mutation", "expected_reason"),
    [
        ("schema", "output_schema"),
        ("section", "section_mismatch"),
        ("citations", "citation_mismatch"),
        ("unsupported", "unsupported_facts"),
        ("missing_owned", "missing_owned_facts"),
        ("conditional", "claim_rendering_mismatch"),
        ("body", "body_claim_mismatch"),
    ],
)
async def test_v3_validation_predicates_are_distinguishable_offline(mutation: str, expected_reason: str) -> None:
    facts = _middle_facts(contract_version="child-guidance-facts-v3")

    class MutatedProvider(MockChildSegmentProvider):
        async def generate_segment(self, *, prompt: str, section_input: ChildSectionRenderInput) -> dict[str, Any]:
            output = await super().generate_segment(prompt=prompt, section_input=section_input)
            if mutation == "schema":
                del output["claims"]
            elif mutation == "section":
                output["title"] = "PRIVATE different title"
            elif mutation == "citations":
                output["cited_fact_ids"] = ["PRIVATE citation"]
            elif mutation == "unsupported":
                output["cited_fact_ids"][0] = output["claims"][0]["fact_ids"][0] = "PRIVATE citation"
            elif mutation == "missing_owned":
                output["claims"].pop()
                output["cited_fact_ids"].pop()
            elif mutation == "conditional":
                output["claims"][0]["conditional"] = not output["claims"][0]["conditional"]
            elif mutation == "body":
                output["body"] += " PRIVATE uncited text"
            return output

    sections = build_child_section_inputs(facts)
    section = max(sections, key=lambda item: len(item.owned_facts)) if mutation == "missing_owned" else sections[0]
    assert len(section.owned_facts) > (1 if mutation == "missing_owned" else 0)
    row = await run_child_segment_generation(provider=MutatedProvider(), section_input=section, guidance_facts=facts)
    assert row.status == "failed"
    assert row.diagnostics["validation_reason"] == expected_reason
    assert "PRIVATE" not in str(row.diagnostics)


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["PRIVATE exception payload", ["claim_rendering_mismatch"], None])
async def test_v3_untrusted_reason_cannot_leak_provider_content(reason: Any) -> None:
    facts = _middle_facts(contract_version="child-guidance-facts-v3")

    class PrivateReasonProvider(MockChildSegmentProvider):
        async def generate_segment(self, *, prompt: str, section_input: ChildSectionRenderInput) -> dict[str, Any]:
            raise ChildNarrativeValidationError("PRIVATE exception payload", reason_code=reason)

    row = await run_child_segment_generation(
        provider=PrivateReasonProvider(), section_input=build_child_section_inputs(facts)[0], guidance_facts=facts
    )
    assert row.diagnostics["validation_reason"] == "contract_validation"
    assert "PRIVATE" not in str(row.diagnostics)


@pytest.mark.asyncio
@pytest.mark.parametrize("version", ["child-guidance-facts-v1", "child-guidance-facts-v2"])
async def test_historical_failure_diagnostics_do_not_change(version: str) -> None:
    from tests.unit.test_child.test_narrative_pipeline import _facts

    facts = _facts() if version.endswith("v1") else _middle_facts(contract_version=version)

    class RejectedProvider(MockChildSegmentProvider):
        async def generate_segment(self, *, prompt: str, section_input: ChildSectionRenderInput) -> dict[str, Any]:
            output = await super().generate_segment(prompt=prompt, section_input=section_input)
            output["body"] += " PRIVATE uncited text"
            return output

    row = await run_child_segment_generation(
        provider=RejectedProvider(), section_input=build_child_section_inputs(facts)[0], guidance_facts=facts
    )
    assert row.status == "failed"
    assert row.diagnostics["error_type"] == "validation_error"
    assert "validation_reason" not in row.diagnostics
