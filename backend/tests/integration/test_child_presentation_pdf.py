from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.child import models
from app.modules.child.presentation import build_child_report_presentation
from app.modules.child.repository import ChildLineageMismatchError, ChildRepository
from app.modules.child.service import run_claimed_full_generation
from tests.integration.test_child_generation_lifecycle import NOW, CountingProvider, _seed_claimable_full_pipeline

pytestmark = [pytest.mark.asyncio, pytest.mark.usefixtures("_setup_database")]


async def test_persisted_child_presentation_keeps_ready_report_and_rejects_unlinked_age(
    db_session: AsyncSession,
) -> None:
    seed, generation = await _seed_claimable_full_pipeline(db_session, idempotency_key="presentation")
    repository = ChildRepository(db_session)
    claim = await repository.claim_generation(
        generation_id=generation.generation_id, task_id="presentation", now=NOW, lease_duration=timedelta(minutes=5)
    )
    assert claim is not None
    await db_session.commit()
    result = await run_claimed_full_generation(db_session, claim=claim, provider=CountingProvider(), now=NOW)
    assert result.report_id is not None
    manifest = await build_child_report_presentation(
        db_session, owner_user_id=seed.owner_id, report_id=result.report_id
    )
    assert manifest["status"] == "ready"
    core_age_id = manifest["metadata"]["age_snapshot_id"]
    assert manifest["age"]["age_snapshot_id"] == core_age_id
    assert len(manifest["sections"]) == 15
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
