"""Independent S11 recovery and transport regressions on disposable PostgreSQL."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import httpx
import pytest
import respx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.child import models
from app.modules.child.repository import ChildRepository
from app.modules.child.service import (
    accept_narrative_retry_generation,
    run_claimed_full_generation,
    run_claimed_narrative_retry,
)
from tests.integration.test_child_generation_lifecycle import NOW, CountingProvider, _seed_claimable_full_pipeline

pytestmark = pytest.mark.usefixtures("_setup_database")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure_mode, corruption",
    [
        ("first", None),
        ("after_completed", None),
        ("disabled", None),
        ("first", "omit"),
        ("first", "hash"),
        ("first", "extra"),
    ],
)
async def test_manual_recovery_completes_sections_missing_after_first_call_exhaustion(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, failure_mode: str, corruption: str | None
) -> None:
    from app.modules.child.narrative import ChildSectionRenderInput, DisabledChildSegmentProvider

    seed, source = await _seed_claimable_full_pipeline(db_session, idempotency_key="review-exhaustion")
    repository = ChildRepository(db_session)
    clock = NOW

    class EarlyFailure(CountingProvider):
        async def generate_segment(self, *, prompt: str, section_input: ChildSectionRenderInput) -> dict[str, Any]:
            self.fail = failure_mode == "first" or self.calls >= 1
            return await super().generate_segment(prompt=prompt, section_input=section_input)

    provider = EarlyFailure()
    for attempt in range(1 if failure_mode == "disabled" else 3):
        claim = await repository.claim_generation(
            generation_id=source.generation_id,
            task_id=f"attempt-{attempt}",
            now=clock,
            lease_duration=timedelta(minutes=5),
        )
        assert claim is not None
        await db_session.commit()
        failed = await run_claimed_full_generation(
            db_session,
            claim=claim,
            provider=DisabledChildSegmentProvider() if failure_mode == "disabled" else provider,
            now=clock,
        )
        clock += timedelta(seconds=30 * 2**attempt)
    assert failed.status == "narrative_failed"
    assert failed.report_id is not None
    assert len(set(provider.section_keys)) == {"first": 1, "after_completed": 2, "disabled": 0}[failure_mode]
    if failure_mode == "disabled":
        assert failed.provider_calls == 0
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
    source_rows = await repository.list_segment_generations(
        child_profile_id=seed.child_id, generation_id=source.generation_id
    )
    source_before = [(row.id, row.status, row.content, dict(row.diagnostics)) for row in source_rows]

    async def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("manual recovery must not recompute deterministic artifacts")

    for method in ("create_parent_style_profile", "create_child_need_profile", "create_interaction_profile"):
        monkeypatch.setattr(ChildRepository, method, forbidden)
    accepted = await accept_narrative_retry_generation(
        db_session,
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        source_report_id=failed.report_id,
        idempotency_key="review-recover",
        dispatcher=lambda *, generation_id: f"child-generation-{generation_id}",
        now=clock,
    )
    if corruption:
        generation = await db_session.scalar(
            select(models.ChildGeneration).where(models.ChildGeneration.generation_id == accepted.generation_id)
        )
        assert generation is not None
        payload = dict(generation.operation_payload)
        pins = [dict(pin) for pin in payload["missing_section_pins"]]
        assert pins
        if corruption == "omit":
            pins.pop()
        elif corruption == "hash":
            pins[0]["input_hash"] = "0" * 64
        else:
            pins.append({"section_key": provider.section_keys[0], "input_hash": "0" * 64})
        payload["missing_section_pins"] = pins
        await db_session.execute(
            update(models.ChildGeneration)
            .where(models.ChildGeneration.generation_id == accepted.generation_id)
            .values(operation_payload=payload)
        )
        await db_session.commit()
    clock += timedelta(seconds=30)
    claim = await repository.claim_generation(
        generation_id=accepted.generation_id,
        task_id="manual",
        now=clock,
        lease_duration=timedelta(minutes=5),
    )
    assert claim is not None
    await db_session.commit()
    healthy = CountingProvider()
    result = await run_claimed_narrative_retry(db_session, claim=claim, provider=healthy, now=clock)
    if corruption:
        assert result.status != "ready"
        assert healthy.calls == result.provider_calls == 0
        assert await snapshot() == before
        return
    assert result.status == "ready"
    assert len(healthy.section_keys) > 1
    assert await snapshot() == before
    source_after = await repository.list_segment_generations(
        child_profile_id=seed.child_id, generation_id=source.generation_id
    )
    assert [(row.id, row.status, row.content, row.diagnostics) for row in source_after] == source_before


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", ["deepseek", "openrouter"])
@pytest.mark.parametrize(
    "transport_error", [httpx.ReadTimeout, httpx.WriteTimeout, httpx.ReadError, httpx.RemoteProtocolError]
)
@pytest.mark.parametrize("retry_path", [False, True], ids=["full", "narrative-retry"])
async def test_configured_child_transport_unknown_is_one_post_and_never_recalled(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    provider_name: str,
    transport_error: type[httpx.TransportError],
    retry_path: bool,
) -> None:
    from app.modules.child.narrative import DisabledChildSegmentProvider
    from app.modules.child.repository import ChildLineageMismatchError
    from app.modules.child.service import configured_child_provider

    for name, value in {
        "LLM_ENABLED": True,
        "LLM_PROVIDER": provider_name,
        "LLM_MODEL": "review-model",
        "LLM_API_KEY": "test-no-network",
        "LLM_MAX_RETRIES": 1,
    }.items():
        monkeypatch.setattr(f"app.modules.child.service.settings.{name}", value)
    seed, source = await _seed_claimable_full_pipeline(db_session, idempotency_key="review-transport")
    repository = ChildRepository(db_session)
    claim = await repository.claim_generation(
        generation_id=source.generation_id,
        task_id="transport",
        now=NOW,
        lease_duration=timedelta(minutes=5),
    )
    assert claim is not None
    await db_session.commit()
    generation_id = source.generation_id
    clock = NOW
    run = run_claimed_full_generation
    if retry_path:
        disabled = await run_claimed_full_generation(
            db_session, claim=claim, provider=DisabledChildSegmentProvider(), now=clock
        )
        assert disabled.report_id is not None
        accepted = await accept_narrative_retry_generation(
            db_session,
            owner_user_id=seed.owner_id,
            child_profile_id=seed.child_id,
            source_report_id=disabled.report_id,
            idempotency_key="review-transport-retry",
            dispatcher=lambda *, generation_id: f"child-generation-{generation_id}",
            now=clock,
        )
        sibling = await accept_narrative_retry_generation(
            db_session,
            owner_user_id=seed.owner_id,
            child_profile_id=seed.child_id,
            source_report_id=disabled.report_id,
            idempotency_key="review-already-queued-sibling",
            dispatcher=lambda *, generation_id: f"child-generation-{generation_id}",
            now=clock,
        )
        generation_id = accepted.generation_id
        clock += timedelta(seconds=30)
        claim = await repository.claim_generation(
            generation_id=generation_id,
            task_id="transport-retry",
            now=clock,
            lease_duration=timedelta(minutes=5),
        )
        assert claim is not None
        await db_session.commit()
        run = run_claimed_narrative_retry
    url = (
        "https://api.deepseek.com/chat/completions"
        if provider_name == "deepseek"
        else "https://openrouter.ai/api/v1/chat/completions"
    )
    with respx.mock(assert_all_called=True) as router:
        route = router.post(url).mock(side_effect=transport_error("remote outcome unknown"))
        result = await run(db_session, claim=claim, provider=configured_child_provider(), now=clock)
    assert route.call_count == result.provider_calls
    assert result.status == "narrative_failed"
    assert result.report_id is not None
    rows = await repository.list_segment_generations(child_profile_id=seed.child_id, generation_id=generation_id)
    failed = [row for row in rows if row.status == "failed"]
    assert len(failed) == route.call_count > 0
    assert all(row.error_code == "child_narrative_provider_outcome_unknown" for row in failed)
    assert all(row.diagnostics["attempts"] == 1 for row in failed)
    if retry_path:
        sibling_claim = await repository.claim_generation(
            generation_id=sibling.generation_id,
            task_id="sibling",
            now=clock,
            lease_duration=timedelta(minutes=5),
        )
        assert sibling_claim is not None
        await db_session.commit()
        healthy = CountingProvider()
        fenced = await run_claimed_narrative_retry(db_session, claim=sibling_claim, provider=healthy, now=clock)
        assert fenced.status != "ready"
        assert fenced.provider_calls == healthy.calls == 0
        with pytest.raises(ChildLineageMismatchError, match="unknown"):
            await accept_narrative_retry_generation(
                db_session,
                owner_user_id=seed.owner_id,
                child_profile_id=seed.child_id,
                source_report_id=result.report_id,
                idempotency_key="review-unknown-second-manual",
                dispatcher=lambda *, generation_id: f"child-generation-{generation_id}",
                now=clock,
            )
        return
    accepted = await accept_narrative_retry_generation(
        db_session,
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        source_report_id=result.report_id,
        idempotency_key="review-unknown-manual",
        dispatcher=lambda *, generation_id: f"child-generation-{generation_id}",
        now=NOW,
    )
    clock = NOW + timedelta(seconds=30)
    retry_claim = await repository.claim_generation(
        generation_id=accepted.generation_id,
        task_id="manual",
        now=clock,
        lease_duration=timedelta(minutes=5),
    )
    assert retry_claim is not None
    await db_session.commit()
    healthy = CountingProvider()
    retried = await run_claimed_narrative_retry(db_session, claim=retry_claim, provider=healthy, now=clock)
    assert retried.status == "narrative_failed"
    assert healthy.calls == retried.provider_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", ["deepseek", "openrouter"])
async def test_configured_explicit_rejection_retains_durable_backoff(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, provider_name: str
) -> None:
    from app.modules.child.service import configured_child_provider

    for name, value in {
        "LLM_ENABLED": True,
        "LLM_PROVIDER": provider_name,
        "LLM_MODEL": "review-model",
        "LLM_API_KEY": "test-no-network",
        "LLM_MAX_RETRIES": 4,
    }.items():
        monkeypatch.setattr(f"app.modules.child.service.settings.{name}", value)
    seed, source = await _seed_claimable_full_pipeline(db_session, idempotency_key="review-rejection")
    repository = ChildRepository(db_session)
    claim = await repository.claim_generation(
        generation_id=source.generation_id,
        task_id="rejection",
        now=NOW,
        lease_duration=timedelta(minutes=5),
    )
    assert claim is not None
    await db_session.commit()
    url = (
        "https://api.deepseek.com/chat/completions"
        if provider_name == "deepseek"
        else "https://openrouter.ai/api/v1/chat/completions"
    )
    with respx.mock(assert_all_called=True) as router:
        route = router.post(url).respond(429, json={"error": "explicit rejection"})
        result = await run_claimed_full_generation(
            db_session, claim=claim, provider=configured_child_provider(), now=NOW
        )
    assert route.call_count == result.provider_calls == 1
    assert result.status == "narrative_retry_waiting"
    assert (
        await repository.claim_generation(
            generation_id=source.generation_id,
            task_id="too-early",
            now=NOW + timedelta(seconds=29),
            lease_duration=timedelta(minutes=5),
        )
        is None
    )
    clock = NOW + timedelta(seconds=30)
    recovered_claim = await repository.claim_generation(
        generation_id=source.generation_id,
        task_id="recovery",
        now=clock,
        lease_duration=timedelta(minutes=5),
    )
    assert recovered_claim is not None
    await db_session.commit()
    healthy = CountingProvider()
    # Automatic retries retain the provider/model identity of their durable intent.
    healthy.provider_name = provider_name
    healthy.model_name = configured_child_provider().model_name
    recovered = await run_claimed_full_generation(db_session, claim=recovered_claim, provider=healthy, now=clock)
    assert recovered.status == "ready"
    rows = await repository.list_segment_generations(child_profile_id=seed.child_id, generation_id=source.generation_id)
    assert all(row.error_code is None for row in rows)
