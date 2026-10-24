"""Sibling retry claims must fence each other across real PostgreSQL sessions."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.child import models
from app.modules.child.guidance_facts import ChildGuidanceFactsRepository
from app.modules.child.narrative import ChildSectionRenderInput, DisabledChildSegmentProvider
from app.modules.child.repository import ChildLineageMismatchError, ChildRepository
from app.modules.child.service import (
    accept_narrative_retry_generation,
    run_claimed_full_generation,
    run_claimed_narrative_retry,
)
from tests.integration.test_child_generation_lifecycle import NOW, CountingProvider, _seed_claimable_full_pipeline

pytestmark = pytest.mark.usefixtures("_setup_database")


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["unknown", "in_flight", "completed", "crash", "rejected", "atomic"])
async def test_sibling_provider_claims_obey_durable_source_section_fence(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    seed, source = await _seed_claimable_full_pipeline(db_session, idempotency_key="concurrent-source")
    repository = ChildRepository(db_session)
    claim = await repository.claim_generation(
        generation_id=source.generation_id, task_id="source", now=NOW, lease_duration=timedelta(minutes=5)
    )
    assert claim is not None
    await db_session.commit()
    failed = await run_claimed_full_generation(
        db_session, claim=claim, provider=DisabledChildSegmentProvider(), now=NOW
    )
    assert failed.report_id is not None
    deterministic_models = (
        models.ChildParentStyleScore,
        models.ChildNeedScore,
        models.ChildInteractionScore,
        models.ChildSynastryEvidence,
        models.ChildContextResolution,
        models.ChildGuidanceFacts,
        models.ChildReport,
    )

    async def deterministic_snapshot() -> dict[str, list[dict[str, Any]]]:
        return {
            model.__tablename__: [
                dict(row) for row in (await db_session.execute(select(model.__table__).order_by(model.id))).mappings()
            ]
            for model in deterministic_models
        }

    deterministic_before = await deterministic_snapshot()
    source_before = [
        dict(row)
        for row in (
            await db_session.execute(
                select(models.ChildSegmentGeneration.__table__)
                .where(models.ChildSegmentGeneration.generation_id == source.generation_id)
                .order_by(models.ChildSegmentGeneration.section_key)
            )
        ).mappings()
    ]
    accepted = [
        await accept_narrative_retry_generation(
            db_session,
            owner_user_id=seed.owner_id,
            child_profile_id=seed.child_id,
            source_report_id=failed.report_id,
            idempotency_key=f"sibling-{index}",
            dispatcher=lambda *, generation_id: f"child-generation-{generation_id}",
            now=NOW,
        )
        for index in range(2)
    ]
    clock = NOW + timedelta(seconds=30)
    claims = []
    for item in accepted:
        sibling_claim = await repository.claim_generation(
            generation_id=item.generation_id, task_id="sibling", now=clock, lease_duration=timedelta(minutes=5)
        )
        assert sibling_claim is not None
        claims.append(sibling_claim)
    await db_session.commit()
    if outcome == "atomic":
        # A has inserted its durable intent but NOT committed it. B must wait
        # inside PostgreSQL, then observe A's commit instead of also inserting.
        template = source_before[0]

        def intent(index: int) -> models.ChildSegmentGeneration:
            return models.ChildSegmentGeneration(
                child_profile_id=seed.child_id,
                generation_id=accepted[index].generation_id,
                section_key=template["section_key"],
                status="in_progress",
                prompt_version=template["prompt_version"],
                model=template["model"],
                lifecycle_token=claims[index].claim_token,
                diagnostics=dict(template["diagnostics"]),
            )

        factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
        async with factory() as a, factory() as b, factory() as observer:
            assert (
                await ChildRepository(a).claim_segment_intent(row=intent(0), claim_token=claims[0].claim_token)
                == "claimed"
            )
            pid = await b.scalar(text("SELECT pg_backend_pid()"))
            pending = asyncio.create_task(
                ChildRepository(b).claim_segment_intent(row=intent(1), claim_token=claims[1].claim_token)
            )
            try:
                for _ in range(200):
                    waiting = await observer.scalar(
                        text(
                            "SELECT EXISTS (SELECT 1 FROM pg_locks "
                            "WHERE pid = :pid AND locktype = 'advisory' AND NOT granted)"
                        ),
                        {"pid": pid},
                    )
                    if waiting or pending.done():
                        break
                    await asyncio.sleep(0.01)
                assert waiting, "sibling must wait on the atomic database claim"
                assert not pending.done()
                await a.commit()
                with pytest.raises(ChildLineageMismatchError, match="fenced"):
                    await asyncio.wait_for(pending, timeout=10)
            finally:
                if not pending.done():
                    pending.cancel()
                    await asyncio.gather(pending, return_exceptions=True)
        return
    # Both workers reach their first intent only AFTER reading the old sibling
    # precheck. Hold B there until A's intent/outcome is durably visible.
    barrier = asyncio.Barrier(2)
    let_b_claim = asyncio.Event()
    a_provider_entered = asyncio.Event()
    b_finished = asyncio.Event()
    original = ChildRepository.claim_segment_intent
    original_load = ChildGuidanceFactsRepository.load_domain_facts
    first = set()

    async def past_precheck(self: ChildGuidanceFactsRepository, **kwargs: Any) -> Any:
        await asyncio.wait_for(barrier.wait(), timeout=10)
        if self.session.info.get("worker") == "b":
            await asyncio.wait_for(a_provider_entered.wait(), timeout=10)
        return await original_load(self, **kwargs)

    monkeypatch.setattr(ChildGuidanceFactsRepository, "load_domain_facts", past_precheck)

    async def gated_claim(self: ChildRepository, **kwargs: Any) -> str:
        generation_id = kwargs["row"].generation_id
        if generation_id not in first:
            first.add(generation_id)
            if generation_id == accepted[1].generation_id:
                await asyncio.wait_for(let_b_claim.wait(), timeout=10)
        return await original(self, **kwargs)

    monkeypatch.setattr(ChildRepository, "claim_segment_intent", gated_claim)

    class WorkerCrash(BaseException):
        pass

    class FirstProvider(CountingProvider):
        async def generate_segment(self, *, prompt: str, section_input: ChildSectionRenderInput) -> dict[str, Any]:
            a_provider_entered.set()
            if not self.calls and outcome in {"in_flight", "crash"}:
                let_b_claim.set()
                await asyncio.wait_for(b_finished.wait(), timeout=10)
            if outcome == "crash":
                self.calls += 1
                self.section_keys.append(section_input.section_key)
                raise WorkerCrash
            if outcome == "unknown":
                self.calls += 1
                self.section_keys.append(section_input.section_key)
                raise httpx.ReadTimeout("response lost")
            return await super().generate_segment(prompt=prompt, section_input=section_input)

    first_provider = FirstProvider(fail=outcome == "rejected")
    second_provider = CountingProvider()
    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)

    async def worker_a() -> None:
        try:
            async with factory() as session:
                await run_claimed_narrative_retry(session, claim=claims[0], provider=first_provider, now=clock)
        except WorkerCrash:
            pass
        finally:
            let_b_claim.set()

    async def worker_b() -> None:
        try:
            async with factory() as session:
                session.info["worker"] = "b"
                result = await run_claimed_narrative_retry(
                    session, claim=claims[1], provider=second_provider, now=clock
                )
                if outcome == "rejected":
                    assert result.status == "ready"
                    assert result.provider_calls > 0
                else:
                    assert result.status != "ready"
                    assert result.provider_calls == 0
        finally:
            b_finished.set()

    await asyncio.wait_for(asyncio.gather(worker_a(), worker_b()), timeout=30)
    assert len(first) == 2
    assert first_provider.calls > 0
    assert (second_provider.calls > 0) == (outcome == "rejected")
    if outcome == "crash":
        monkeypatch.setattr(ChildGuidanceFactsRepository, "load_domain_facts", original_load)
        # A died with an already committed intent: even a new lease cannot
        # recall that section, nor can B's rejection erase the intent.
        await repository.reconcile_stuck_generations(now=clock + timedelta(minutes=16), max_attempts=3)
        await db_session.commit()
        recovered = await repository.claim_generation(
            generation_id=accepted[0].generation_id,
            task_id="redelivery",
            now=clock + timedelta(minutes=17),
            lease_duration=timedelta(minutes=5),
        )
        assert recovered is not None
        await db_session.commit()
        healthy = CountingProvider()
        await run_claimed_narrative_retry(
            db_session, claim=recovered, provider=healthy, now=clock + timedelta(minutes=16)
        )
        assert first_provider.section_keys[0] not in healthy.section_keys
        row = await db_session.scalar(
            select(models.ChildSegmentGeneration).where(
                models.ChildSegmentGeneration.generation_id == accepted[0].generation_id,
                models.ChildSegmentGeneration.section_key == first_provider.section_keys[0],
            )
        )
        assert row is not None
        assert row.error_code == "child_narrative_provider_outcome_unknown"
    source_after = [
        dict(row)
        for row in (
            await db_session.execute(
                select(models.ChildSegmentGeneration.__table__)
                .where(models.ChildSegmentGeneration.generation_id == source.generation_id)
                .order_by(models.ChildSegmentGeneration.section_key)
            )
        ).mappings()
    ]
    assert source_after == source_before
    assert await deterministic_snapshot() == deterministic_before
