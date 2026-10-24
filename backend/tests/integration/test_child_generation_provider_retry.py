"""Provider lifecycle durability against real PostgreSQL transaction boundaries."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.child import models
from app.modules.child.narrative import ChildSectionRenderInput
from app.modules.child.repository import ChildRepository
from app.modules.child.service import (
    _source_segment_pin,
    _source_segment_pin_hash,
    accept_narrative_retry_generation,
    run_claimed_full_generation,
    run_claimed_narrative_retry,
)
from tests.integration.test_child_generation_lifecycle import (
    NOW,
    CountingProvider,
    SelectiveProvider,
    _seed_claimable_full_pipeline,
)

pytestmark = pytest.mark.usefixtures("_setup_database")


@pytest.mark.asyncio
@pytest.mark.parametrize("narrative_retry", [False, True], ids=["full", "narrative-retry"])
async def test_provider_response_crash_reports_attempt_and_fences_recovery(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    narrative_retry: bool,
) -> None:
    seed, source = await _seed_claimable_full_pipeline(db_session, idempotency_key="provider-response-crash")
    repository = ChildRepository(db_session)
    generation_id = source.generation_id
    clock = NOW
    claim = await repository.claim_generation(
        generation_id=generation_id, task_id="source", now=clock, lease_duration=timedelta(minutes=5)
    )
    assert claim is not None
    await db_session.commit()
    run = run_claimed_full_generation
    if narrative_retry:
        failed = await run_claimed_full_generation(
            db_session, claim=claim, provider=SelectiveProvider(failed_sections={"parent_style"}), now=clock
        )
        assert failed.report_id is not None
        accepted = await accept_narrative_retry_generation(
            db_session,
            owner_user_id=seed.owner_id,
            child_profile_id=seed.child_id,
            source_report_id=failed.report_id,
            idempotency_key="retry-response-crash",
            dispatcher=lambda *, generation_id: f"child-generation-{generation_id}",
            now=clock,
        )
        generation_id = accepted.generation_id
        clock += timedelta(seconds=30)
        claim = await repository.claim_generation(
            generation_id=generation_id, task_id="retry", now=clock, lease_duration=timedelta(minutes=5)
        )
        assert claim is not None
        await db_session.commit()
        run = run_claimed_narrative_retry

    original = ChildRepository.persist_terminal_segment
    crashed = False

    async def crash_after_response(
        self: ChildRepository, *, row: models.ChildSegmentGeneration, claim_token: UUID | None = None
    ) -> models.ChildSegmentGeneration:
        nonlocal crashed
        if row.status == "ready" and not crashed:
            crashed = True
            raise RuntimeError("provider succeeded but persistence failed")
        return await original(self, row=row, claim_token=claim_token)

    monkeypatch.setattr(ChildRepository, "persist_terminal_segment", crash_after_response)
    provider = CountingProvider()
    result = await run(db_session, claim=claim, provider=provider, now=clock)
    assert result.status == "narrative_retry_waiting"
    assert provider.calls == result.provider_calls == 1
    first_section = provider.section_keys[0]
    recovered_claim = await repository.claim_generation(
        generation_id=generation_id,
        task_id="recovery",
        now=clock + timedelta(seconds=30),
        lease_duration=timedelta(minutes=5),
    )
    assert recovered_claim is not None
    await db_session.commit()
    recovered = await run(db_session, claim=recovered_claim, provider=provider, now=clock + timedelta(seconds=30))
    assert recovered.status == "narrative_failed"
    assert provider.section_keys.count(first_section) == 1
    segment = await db_session.scalar(
        select(models.ChildSegmentGeneration)
        .where(
            models.ChildSegmentGeneration.generation_id == generation_id,
            models.ChildSegmentGeneration.section_key == first_section,
        )
        .execution_options(populate_existing=True)
    )
    assert segment is not None
    assert segment.error_code == "child_narrative_provider_outcome_unknown"


@pytest.mark.asyncio
async def test_narrative_retry_backoff_starts_after_provider_failure_not_before_call(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed, source = await _seed_claimable_full_pipeline(db_session, idempotency_key="retry-live-clock")
    repository = ChildRepository(db_session)
    source_claim = await repository.claim_generation(
        generation_id=source.generation_id, task_id="source", now=NOW, lease_duration=timedelta(minutes=5)
    )
    assert source_claim is not None
    await db_session.commit()
    failed = await run_claimed_full_generation(
        db_session, claim=source_claim, provider=SelectiveProvider(failed_sections={"parent_style"}), now=NOW
    )
    assert failed.report_id is not None
    accepted = await accept_narrative_retry_generation(
        db_session,
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        source_report_id=failed.report_id,
        idempotency_key="retry-live-clock",
        dispatcher=lambda *, generation_id: f"child-generation-{generation_id}",
        now=NOW,
    )
    started = NOW + timedelta(seconds=30)
    claim = await repository.claim_generation(
        generation_id=accepted.generation_id, task_id="retry", now=started, lease_duration=timedelta(minutes=5)
    )
    assert claim is not None
    await db_session.commit()
    clock = started

    class LiveClock:
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            return clock

    class SlowFailure(CountingProvider):
        async def generate_segment(self, *, prompt: str, section_input: ChildSectionRenderInput) -> dict[str, Any]:
            nonlocal clock
            clock += timedelta(seconds=90)
            return await super().generate_segment(prompt=prompt, section_input=section_input)

    monkeypatch.setattr("app.modules.child.service.datetime", LiveClock)
    result = await run_claimed_narrative_retry(db_session, claim=claim, provider=SlowFailure(fail=True))
    assert result.status == "narrative_retry_waiting"
    persisted = await db_session.scalar(
        select(models.ChildGeneration)
        .where(models.ChildGeneration.generation_id == accepted.generation_id)
        .execution_options(populate_existing=True)
    )
    assert persisted is not None
    assert persisted.heartbeat_at == clock
    assert persisted.next_retry_at == clock + timedelta(seconds=30)


@pytest.mark.asyncio
@pytest.mark.parametrize("corruption", ["non_failed", "missing_failed"])
async def test_retry_rejects_changed_failed_section_scope_before_provider_call(
    db_session: AsyncSession, corruption: str
) -> None:
    seed, source = await _seed_claimable_full_pipeline(db_session, idempotency_key="retry-scope")
    repository = ChildRepository(db_session)
    source_claim = await repository.claim_generation(
        generation_id=source.generation_id, task_id="source", now=NOW, lease_duration=timedelta(minutes=5)
    )
    assert source_claim is not None
    await db_session.commit()
    failed = await run_claimed_full_generation(
        db_session,
        claim=source_claim,
        provider=SelectiveProvider(failed_sections={"parent_style", "child_interaction_needs"}),
        now=NOW,
    )
    assert failed.report_id is not None
    accepted = await accept_narrative_retry_generation(
        db_session,
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        source_report_id=failed.report_id,
        idempotency_key="retry-scope",
        dispatcher=lambda *, generation_id: f"child-generation-{generation_id}",
        now=NOW,
    )
    generation = await db_session.scalar(
        select(models.ChildGeneration).where(models.ChildGeneration.generation_id == accepted.generation_id)
    )
    assert generation is not None
    payload = dict(generation.operation_payload)
    pins = list(payload["failed_section_pins"])
    assert len(pins) == 2
    if corruption == "non_failed":
        ready = await db_session.scalar(
            select(models.ChildSegmentGeneration).where(
                models.ChildSegmentGeneration.generation_id == source.generation_id,
                models.ChildSegmentGeneration.status == "ready",
            )
        )
        assert ready is not None
        pin = _source_segment_pin(ready)
        pins.append(pin | {"pin_hash": _source_segment_pin_hash(pin)})
    else:
        pins.pop()
    payload["failed_section_pins"] = pins
    await db_session.execute(
        update(models.ChildGeneration)
        .where(models.ChildGeneration.generation_id == accepted.generation_id)
        .values(operation_payload=payload)
    )
    await db_session.commit()
    claim = await repository.claim_generation(
        generation_id=accepted.generation_id,
        task_id="retry",
        now=NOW + timedelta(seconds=30),
        lease_duration=timedelta(minutes=5),
    )
    assert claim is not None
    await db_session.commit()
    provider = CountingProvider()
    result = await run_claimed_narrative_retry(
        db_session, claim=claim, provider=provider, now=NOW + timedelta(seconds=30)
    )
    assert provider.calls == 0
    assert result.status != "ready"


@pytest.mark.asyncio
@pytest.mark.parametrize("narrative_retry", [False, True], ids=["full", "narrative-retry"])
async def test_provider_intents_are_committed_and_recovery_preserves_completed_sections(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, narrative_retry: bool
) -> None:
    seed, source = await _seed_claimable_full_pipeline(db_session, idempotency_key="durable-recovery")
    repository = ChildRepository(db_session)
    generation_id = source.generation_id
    clock = NOW
    claim = await repository.claim_generation(
        generation_id=generation_id, task_id="source", now=clock, lease_duration=timedelta(minutes=5)
    )
    assert claim is not None
    await db_session.commit()
    run = run_claimed_full_generation
    if narrative_retry:
        failed = await run_claimed_full_generation(
            db_session,
            claim=claim,
            provider=SelectiveProvider(failed_sections={"parent_style", "child_interaction_needs"}),
            now=clock,
        )
        assert failed.report_id is not None
        accepted = await accept_narrative_retry_generation(
            db_session,
            owner_user_id=seed.owner_id,
            child_profile_id=seed.child_id,
            source_report_id=failed.report_id,
            idempotency_key="durable-recovery-retry",
            dispatcher=lambda *, generation_id: f"child-generation-{generation_id}",
            now=clock,
        )
        generation_id = accepted.generation_id
        clock += timedelta(seconds=30)
        claim = await repository.claim_generation(
            generation_id=generation_id, task_id="retry", now=clock, lease_duration=timedelta(minutes=5)
        )
        assert claim is not None
        await db_session.commit()
        run = run_claimed_narrative_retry

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    observations: list[str] = []

    class ObservedProvider(CountingProvider):
        async def generate_segment(self, *, prompt: str, section_input: ChildSectionRenderInput) -> dict[str, Any]:
            async with factory() as observer:
                intent = await observer.scalar(
                    select(models.ChildSegmentGeneration).where(
                        models.ChildSegmentGeneration.generation_id == generation_id,
                        models.ChildSegmentGeneration.section_key == section_input.section_key,
                    )
                )
                assert intent is not None
                assert intent.status == "in_progress"
                assert intent.lifecycle_token is not None
                observations.append(section_input.section_key)
            self.fail = len(observations) == 2
            return await super().generate_segment(prompt=prompt, section_input=section_input)

    provider = ObservedProvider()
    first = await run(db_session, claim=claim, provider=provider, now=clock)
    assert first.status == "narrative_retry_waiting"
    assert first.report_id is not None
    assert first.provider_calls == provider.calls == 2
    completed_key, failed_key = provider.section_keys
    completed = await db_session.scalar(
        select(models.ChildSegmentGeneration).where(
            models.ChildSegmentGeneration.generation_id == generation_id,
            models.ChildSegmentGeneration.section_key == completed_key,
        )
    )
    assert completed is not None
    completed_identity = (completed.id, completed.content, dict(completed.diagnostics))
    deterministic_models = (
        models.ChildParentStyleScore,
        models.ChildNeedScore,
        models.ChildInteractionScore,
        models.ChildSynastryEvidence,
        models.ChildContextResolution,
        models.ChildGuidanceFacts,
        models.ChildReport,
    )

    async def snapshot() -> dict[str, list[dict[str, Any]]]:
        return {
            model.__tablename__: [
                dict(row) for row in (await db_session.execute(select(model.__table__).order_by(model.id))).mappings()
            ]
            for model in deterministic_models
        }

    before = await snapshot()

    async def forbidden_recomputation(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("recovery must not recompute deterministic profiles")

    for method in ("create_parent_style_profile", "create_child_need_profile", "create_interaction_profile"):
        monkeypatch.setattr(ChildRepository, method, forbidden_recomputation)
    for attempt, delay in ((2, 30), (3, 60)):
        assert (
            await repository.claim_generation(
                generation_id=generation_id,
                task_id="too-early",
                now=clock + timedelta(seconds=delay - 1),
                lease_duration=timedelta(minutes=5),
            )
            is None
        )
        clock += timedelta(seconds=delay)
        claim = await repository.claim_generation(
            generation_id=generation_id,
            task_id=f"recovery-{attempt}",
            now=clock,
            lease_duration=timedelta(minutes=5),
        )
        assert claim is not None
        await db_session.commit()
        recovery_provider = CountingProvider(fail=attempt == 2)
        recovered = await run(db_session, claim=claim, provider=recovery_provider, now=clock)
        assert completed_key not in recovery_provider.section_keys
        if attempt == 2:
            assert recovered.status == "narrative_retry_waiting"
            assert recovery_provider.section_keys == [failed_key]
            assert recovered.provider_calls == 1
        else:
            assert recovered.status == "ready"
            assert recovered.report_id == first.report_id
    await db_session.refresh(completed)
    assert (completed.id, completed.content, completed.diagnostics) == completed_identity
    assert await snapshot() == before
    assert observations == [completed_key, failed_key]


@pytest.mark.asyncio
async def test_default_disabled_provider_publishes_deterministic_report_without_retry_loop(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.modules.child.service import configured_child_provider

    monkeypatch.setattr("app.modules.child.service.settings.LLM_ENABLED", False)
    _, generation = await _seed_claimable_full_pipeline(db_session, idempotency_key="disabled-provider")
    repository = ChildRepository(db_session)
    claim = await repository.claim_generation(
        generation_id=generation.generation_id,
        task_id="disabled-worker",
        now=NOW,
        lease_duration=timedelta(minutes=5),
    )
    assert claim is not None
    await db_session.commit()
    result = await run_claimed_full_generation(db_session, claim=claim, provider=configured_child_provider(), now=NOW)
    assert result.status == "narrative_failed"
    assert result.provider_calls == 0
    assert result.report_id is not None
    report = await db_session.get(models.ChildReport, result.report_id)
    assert report is not None and report.status == "deterministic_ready"
    segments = await repository.list_segment_generations(
        child_profile_id=generation.child_profile_id, generation_id=generation.generation_id
    )
    failed = [row for row in segments if row.status == "failed"]
    assert failed
    assert all(row.error_code == "child_narrative_disabled" for row in failed)
    assert all(row.content is None and row.diagnostics["attempts"] == 0 for row in failed)
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(models.ChildReportAssembly)
            .where(models.ChildReportAssembly.generation_id == generation.generation_id)
        )
        == 1
    )
