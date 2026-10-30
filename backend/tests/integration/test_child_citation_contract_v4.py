"""Real persistence/retry/API/PDF checks for the bounded provider citation contract."""

from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.dependencies import get_current_user
from app.main import app
from app.modules.child import models
from app.modules.child.narrative import ChildSectionRenderInput
from app.modules.child.repository import ChildRepository
from app.modules.child.service import (
    accept_narrative_retry_generation,
    run_claimed_full_generation,
    run_claimed_narrative_retry,
)
from tests.integration.test_child_generation_lifecycle import (
    NOW,
    CountingProvider,
    _grant_direct_child_access,
    _seed_claimable_full_pipeline,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.usefixtures("_setup_database")]


@pytest.mark.parametrize("prompt_version", ["child-section-prompt-v3", "child-section-prompt-v4"])
async def test_persisted_failed_praise_retry_keeps_version_diagnostics_and_api_pdf(
    db_session: AsyncSession, client: AsyncClient, monkeypatch: pytest.MonkeyPatch, prompt_version: str
) -> None:
    seed, generation = await _seed_claimable_full_pipeline(db_session, idempotency_key="citation-version")
    repository = ChildRepository(db_session)
    claim = await repository.claim_generation(
        generation_id=generation.generation_id, task_id="full", now=NOW, lease_duration=timedelta(minutes=5)
    )
    assert claim is not None
    await db_session.commit()

    class RedundantCitationProvider(CountingProvider):
        async def generate_segment(self, *, prompt: str, section_input: ChildSectionRenderInput) -> dict[str, Any]:
            raw = await super().generate_segment(prompt=prompt, section_input=section_input)
            if section_input.section_key == "praise_recognition":
                assert len(section_input.owned_facts) == 1
                assert section_input.owned_facts[0].approved_text.count(".") > 1
                raw["cited_fact_ids"] = ["unknown-private-id"]
            return raw

    initial_provider = RedundantCitationProvider()
    with monkeypatch.context() as historical:
        historical.setattr("app.modules.child.service.CURRENT_CHILD_PROMPT_VERSION", prompt_version)
        initial = await run_claimed_full_generation(db_session, claim=claim, provider=initial_provider, now=NOW)
    assert initial.status == "narrative_failed" and initial.report_id is not None
    report = await db_session.get(models.ChildReport, initial.report_id)
    assert report is not None and report.prompt_version == prompt_version
    source_rows = list(
        (
            await db_session.scalars(
                select(models.ChildSegmentGeneration).where(
                    models.ChildSegmentGeneration.generation_id == generation.generation_id
                )
            )
        ).all()
    )
    praise = next(row for row in source_rows if row.section_key == "praise_recognition")
    expected_reason = "citation_mismatch" if prompt_version.endswith("v3") else "output_schema"
    assert praise.diagnostics["validation_reason"] == expected_reason
    assert praise.content is None and praise.evidence_refs == []
    snapshots = {row.id: deepcopy(row.diagnostics) for row in source_rows}
    facts = await db_session.scalar(
        select(models.ChildGuidanceFacts).where(models.ChildGuidanceFacts.generation_id == generation.generation_id)
    )
    assert facts is not None and facts.contract_version == "child-guidance-facts-v3"
    facts_snapshot = deepcopy(facts.payload), deepcopy(facts.evidence_registry)
    accepted = await accept_narrative_retry_generation(
        db_session,
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        source_report_id=report.id,
        idempotency_key="citation-pinned-retry",
        now=NOW,
        dispatcher=lambda *, generation_id: str(generation_id),
    )
    retry = await db_session.scalar(
        select(models.ChildGeneration).where(models.ChildGeneration.generation_id == accepted.generation_id)
    )
    assert retry is not None
    assert retry.operation_payload.get("narrative_prompt_version") == (
        prompt_version if prompt_version.endswith("v4") else None
    )
    retry_claim = await repository.claim_generation(
        generation_id=accepted.generation_id,
        task_id="retry",
        now=NOW + timedelta(minutes=1),
        lease_duration=timedelta(minutes=5),
    )
    assert retry_claim is not None
    await db_session.commit()

    class PinnedProvider(CountingProvider):
        async def generate_segment(self, *, prompt: str, section_input: ChildSectionRenderInput) -> dict[str, Any]:
            assert prompt_version in prompt
            assert section_input.contract_version.endswith(prompt_version.rsplit("-", 1)[1])
            raw = await super().generate_segment(prompt=prompt, section_input=section_input)
            assert ("cited_fact_ids" in raw) is prompt_version.endswith("v3")
            return raw

    provider = PinnedProvider()
    result = await run_claimed_narrative_retry(
        db_session, claim=retry_claim, provider=provider, now=NOW + timedelta(minutes=1)
    )
    assert result.status == "ready"
    assert provider.calls == 1 and provider.section_keys == ["praise_recognition"]
    assert isinstance(db_session.bind, AsyncEngine)
    async with async_sessionmaker(db_session.bind, expire_on_commit=False)() as reader:
        for row_id, diagnostics in snapshots.items():
            row = await reader.get(models.ChildSegmentGeneration, row_id)
            assert row is not None and row.diagnostics == diagnostics
        preserved_facts = await reader.get(models.ChildGuidanceFacts, facts.id)
        assert preserved_facts is not None
        assert (preserved_facts.payload, preserved_facts.evidence_registry) == facts_snapshot
        assembly = await reader.scalar(
            select(models.ChildReportAssembly).where(models.ChildReportAssembly.generation_id == accepted.generation_id)
        )
        assert assembly is not None and assembly.payload["prompt_version"] == prompt_version
        assert assembly.contract_version == "child_report_narrative_" + prompt_version.rsplit("-", 1)[1]
        retried = await reader.scalar(
            select(models.ChildSegmentGeneration).where(
                models.ChildSegmentGeneration.generation_id == accepted.generation_id
            )
        )
        assert retried is not None and retried.prompt_version == prompt_version
        output = retried.diagnostics["output"]
        assert output["cited_fact_ids"] == [claim["fact_ids"][0] for claim in output["claims"]]
        assert len(output["claims"]) == 1
        assert "validation_reason" not in str(assembly.payload)

    await _grant_direct_child_access(db_session, user_id=seed.owner_id)
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", True)
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    response = await client.get(f"/api/v1/child/reports/{report.id}")
    assert response.status_code == 200, response.text
    presentation = response.json()["presentation"]
    assert presentation["status"] == "ready"
    public_praise = next(section for section in presentation["sections"] if section["key"] == "praise_recognition")
    assert public_praise["body"] == output["body"]
    pdf = await client.get(f"/api/v1/child/reports/{report.id}/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
    from io import BytesIO

    from pypdf import PdfReader

    normalized_pdf = " ".join(
        " ".join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages).replace("\u00ad", "").split()
    )
    assert " ".join(public_praise["body"].split()) in normalized_pdf
