from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.dependencies import get_current_user
from app.main import app
from app.modules.child import models
from app.modules.child.presentation import build_child_report_presentation
from app.modules.child.repository import ChildLineageMismatchError, ChildRepository
from app.modules.child.service import run_claimed_full_generation
from tests.integration.test_child_generation_lifecycle import (
    NOW,
    CountingProvider,
    _grant_direct_child_access,
    _seed_claimable_full_pipeline,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.usefixtures("_setup_database")]


async def test_persisted_child_presentation_keeps_ready_report_and_rejects_unlinked_age(
    db_session: AsyncSession,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed, generation = await _seed_claimable_full_pipeline(db_session, idempotency_key="presentation")

    # Real deterministic scoring over fixture charts, never hand-edited scores:
    # exercise persisted facts -> narrative -> fresh session -> API -> PDF.
    async def unexpected_retry(*args: object, **kwargs: object) -> None:
        import sys

        raise AssertionError("Mock-only full generation unexpectedly retried") from sys.exception()

    monkeypatch.setattr(ChildRepository, "release_generation_for_retry", unexpected_retry)
    repository = ChildRepository(db_session)
    claim = await repository.claim_generation(
        generation_id=generation.generation_id, task_id="presentation", now=NOW, lease_duration=timedelta(minutes=5)
    )
    assert claim is not None
    await db_session.commit()
    result = await run_claimed_full_generation(db_session, claim=claim, provider=CountingProvider(), now=NOW)
    assert result.report_id is not None
    report = await db_session.get(models.ChildReport, result.report_id)
    assert report is not None and report.prompt_version == "child-section-prompt-v5"
    facts_row = await db_session.scalar(
        select(models.ChildGuidanceFacts).where(
            models.ChildGuidanceFacts.generation_id == generation.generation_id,
        )
    )
    assert facts_row is not None and facts_row.contract_version == "child-guidance-facts-v4"
    assert len(facts_row.payload["source_profiles"]) == 26
    manifest = await build_child_report_presentation(
        db_session, owner_user_id=seed.owner_id, report_id=result.report_id
    )
    assert manifest["status"] == "ready"
    assert manifest["quality"]["status"] in {"ready", "limited"}
    by_key = {item["key"]: item for item in manifest["sections"]}
    assert "стиля взрослого" in by_key["parent_style"]["body"]
    assert "возможных потребностей" in by_key["child_interaction_needs"]["body"]
    assert "похвала и признание" in by_key["praise_recognition"]["body"]
    core_age_id = manifest["metadata"]["age_snapshot_id"]
    assert manifest["age"]["age_snapshot_id"] == core_age_id
    assert len(manifest["sections"]) == 15
    for key in (
        "natural_contact",
        "friction_zones",
        "soothing_support",
        "explanation_learning",
        "conflict_cycle",
        "not_personal",
    ):
        assert by_key[key]["status"] == "ready"
        assert by_key[key]["evidence_state"] in {"no_pronounced_skew", "ambiguous_signals", "pronounced_signal"}
    from app.modules.child.content_v4 import INTERACTION_DESTINATIONS

    moderate = [
        item
        for item in facts_row.payload["source_profiles"]
        if item["source_kind"] == "interaction" and item["signal_state"] == "no_pronounced_skew"
    ]
    assert moderate
    for profile in moderate:
        section = by_key[INTERACTION_DESTINATIONS[profile["dimension"]]]
        assert "нет выраженного перекоса" in section["body"]
    await db_session.commit()
    assert isinstance(db_session.bind, AsyncEngine)
    async with async_sessionmaker(db_session.bind, expire_on_commit=False)() as reader:
        assert (
            await build_child_report_presentation(reader, owner_user_id=seed.owner_id, report_id=result.report_id)
            == manifest
        )
    await _grant_direct_child_access(db_session, user_id=seed.owner_id)
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", True)
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    response = await client.get(f"/api/v1/child/reports/{result.report_id}")
    assert response.status_code == 200, response.text
    assert response.json()["presentation"] == manifest
    pdf = await client.get(f"/api/v1/child/reports/{result.report_id}/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-"), pdf.text[:200]
    from io import BytesIO

    from pypdf import PdfReader

    text = " ".join(
        " ".join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages).replace("\u00ad", "").split()
    )
    for key in (
        "natural_contact",
        "friction_zones",
        "soothing_support",
        "explanation_learning",
        "conflict_cycle",
        "not_personal",
    ):
        assert by_key[key]["evidence_note"] in text
    before = await db_session.scalar(select(func.count()).select_from(models.ChildReport))
    candidate = await repository.create_generation_idempotently(
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        parent_chart_id=seed.parent_chart_id,
        child_chart_version_id=seed.child_chart_id,
        operation="narrative_retry",
        idempotency_key="failed-candidate",
        source_report_id=result.report_id,
    )
    await db_session.commit()
    assert candidate.created
    # An unfinished replacement must not replace a complete immutable assembly.
    assert (
        await build_child_report_presentation(db_session, owner_user_id=seed.owner_id, report_id=result.report_id)
        == manifest
    )
    assert await db_session.scalar(select(func.count()).select_from(models.ChildReport)) == before
    for owner, snapshot in ((uuid4(), None), (seed.owner_id, uuid4())):
        with pytest.raises(ChildLineageMismatchError):
            await build_child_report_presentation(
                db_session, owner_user_id=owner, report_id=result.report_id, age_snapshot_id=snapshot
            )
    await db_session.rollback()


async def test_child_age_presentation_is_pinned_and_uses_safe_server_age_actions(
    db_session: AsyncSession,
) -> None:
    seed, generation = await _seed_claimable_full_pipeline(db_session, idempotency_key="age-presentation")
    repository = ChildRepository(db_session)
    claim = await repository.claim_generation(
        generation_id=generation.generation_id, task_id="age-presentation", now=NOW, lease_duration=timedelta(minutes=5)
    )
    assert claim is not None
    await db_session.commit()
    result = await run_claimed_full_generation(db_session, claim=claim, provider=CountingProvider(), now=NOW)
    assert result.report_id is not None
    original = await build_child_report_presentation(
        db_session, owner_user_id=seed.owner_id, report_id=result.report_id
    )
    update = await repository.create_age_update_idempotently(
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        report_id=result.report_id,
        idempotency_key="new-age",
        guidance_rules_version="child-age-guidance-mvp-1",
        payload={"unsafe_untrusted_prose": "must never be rendered"},
        now=NOW + timedelta(days=3),
    )
    await db_session.commit()
    selected = await build_child_report_presentation(
        db_session,
        owner_user_id=seed.owner_id,
        report_id=result.report_id,
        age_snapshot_id=update.snapshot.id,
    )
    assert selected["metadata"]["age_snapshot_id"] == str(update.snapshot.id)
    assert "must never be rendered" not in str(selected)
    assert selected["sections"][-1]["body"] is None
    assert selected["sections"][-1]["actions"]
    from uuid import UUID

    assert (
        await build_child_report_presentation(
            db_session,
            owner_user_id=seed.owner_id,
            report_id=result.report_id,
            age_snapshot_id=UUID(original["metadata"]["age_snapshot_id"]),
        )
        == original
    )
