"""S09 real Postgres tests against an explicitly migrated disposable cluster."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx
import pytest
import respx
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.modules.analytics.costs import Attempt, PinnedRate, TokenUsage
from app.modules.analytics.usage_backfill import BackfillResult, backfill_child_usage, child_usage_projection
from app.modules.analytics.usage_evidence import (
    TransportEvidence,
    model_ref,
    read_transport_costs,
    record_transport_evidence,
    transport_usage,
)
from app.modules.authorization.models import Entitlement
from app.modules.child.models import ChildGeneration, ChildReportAssembly, ChildSegmentGeneration
from app.modules.child.narrative import ChildSectionRenderInput
from app.modules.child.repository import ChildRepository
from app.modules.child.service import run_claimed_full_generation
from app.modules.llm.exceptions import LLMProviderUnavailableError, LLMTimeoutError
from app.modules.llm.providers.deepseek import DeepSeekProvider
from app.modules.payments.models import Payment
from app.modules.subscriptions.models import Subscription, SubscriptionPlan
from tests.integration.test_child_generation_lifecycle import NOW, CountingProvider, _seed_claimable_full_pipeline

pytestmark = pytest.mark.skipif(
    not os.environ.get("E23_S09_DISPOSABLE_DATABASE_URL"),
    reason="explicit migrated E23 S09 disposable database required",
)
_DATABASE = "e23_s09_tests"
_MARKER = "private-fixture-must-not-export"
_MODEL = "synthetic-child-model"
_OBSERVED = {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}
_REJECTED = {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}
_SUCCESS = {"prompt_tokens": 7, "completion_tokens": 2, "total_tokens": 9}


class _Output(BaseModel):
    ok: bool


class _Input(BaseModel):
    secret: str = _MARKER


class _ChildOverFakeTransport(CountingProvider):
    provider_name = "deepseek"
    model_name = model_ref(_MODEL)
    reject_first_section = True

    async def generate_segment(self, *, prompt: str, section_input: ChildSectionRenderInput) -> dict[str, Any]:
        provider = DeepSeekProvider(api_key=_MARKER, model=_MODEL, timeout_seconds=2, max_retries=int(self.calls == 1))
        fixture: Any = _Input()
        await provider.generate_structured(prompt=prompt, narrative_input=fixture, schema=_Output)
        payload = await super().generate_segment(prompt=prompt, section_input=section_input)
        if self.calls == 1 and self.reject_first_section:
            return payload | {"section_key": "synthetic-invalid-section"}
        return payload


@pytest.fixture
async def s09_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(os.environ["E23_S09_DISPOSABLE_DATABASE_URL"], poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT current_database()")) == _DATABASE
            assert await connection.scalar(text("SELECT current_schemas(false)")) == ["public"]
            assert (
                await connection.scalar(
                    text("SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal AND tgname='reject_usage_mutation'")
                )
                == 2
            )
        yield engine
    finally:
        await engine.dispose()


async def _authority(engine: AsyncEngine) -> dict[str, str]:
    async with engine.connect() as connection:
        result = {}
        for table in (
            "users",
            "person_profiles",
            "child_segment_generations",
            "child_generations",
            "child_reports",
            "child_report_assemblies",
            "payments",
            "subscriptions",
            "entitlements",
            "business_events",
            "business_event_outbox",
        ):
            statement = text(f"SELECT to_jsonb(array(SELECT t FROM {table} t ORDER BY id))")  # noqa: S608
            contents = await connection.scalar(statement)
            result[table] = json.dumps(contents, sort_keys=True)
        return result


async def _operator_run(
    engine: AsyncEngine, *, start: datetime, end: datetime, digest: str | None = None, max_rows: int = 5000
) -> BackfillResult:
    async with engine.begin() as conn:
        result = await backfill_child_usage(
            conn, start=start, end=end, expected_database=_DATABASE, apply_digest=digest, max_rows=max_rows
        )
        if digest is None:
            assert await conn.scalar(text("SHOW transaction_read_only")) == "on"
        return result


@respx.mock
async def test_projection_from_real_child_writer_preserves_authority_and_privacy(
    s09_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    start = datetime.now(UTC) - timedelta(minutes=1)
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", False)
    response = {"choices": [{"message": {"content": '{"ok":true}'}}], "usage": _SUCCESS, "raw": _MARKER}
    http_calls = 0

    def respond(_: httpx.Request) -> httpx.Response:
        nonlocal http_calls
        http_calls += 1
        if http_calls == 2:
            return httpx.Response(503, json={"usage": _REJECTED, "raw": _MARKER})
        return httpx.Response(200, json=response)

    route = respx.post("https://api.deepseek.com/chat/completions").mock(side_effect=respond)
    async with async_sessionmaker(s09_engine, expire_on_commit=False)() as db:
        seed, generation = await _seed_claimable_full_pipeline(db, idempotency_key="s09-historical")
        provider = _ChildOverFakeTransport()
        repo = ChildRepository(db)
        claim = await repo.claim_generation(
            generation_id=generation.generation_id,
            task_id="s09-fixture",
            now=NOW,
            lease_duration=timedelta(minutes=5),
        )
        assert claim is not None
        await db.commit()
        await run_claimed_full_generation(db, claim=claim, provider=provider, now=NOW)
        assert route.call_count == provider.calls + 1 > 2
        plan = SubscriptionPlan(plan_code="s09-test", display_name="fixture", amount=7, billing_interval="month")
        db.add(plan)
        await db.flush()
        subscription = Subscription(user_id=seed.owner_id, plan_id=plan.id)
        db.add(subscription)
        await db.flush()
        payment = Payment(user_id=seed.owner_id, subscription_id=subscription.id, provider="fixture", amount=7)
        db.add(payment)
        await db.flush()
        db.add(Entitlement(user_id=seed.owner_id, source_payment_id=payment.id, starts_at=NOW, product="fixture"))
        # Historical input test cases outside the canonical producer: an older
        # terminal failure with unavailable diagnostics and a hostile usage leaf.
        for key, usage in (
            ("s09_missing", None),
            ("s09_bad", {"http_attempts": 2, "responses_with_usage": 1, "generated_text": _MARKER}),
            ("s09_zero", {"http_attempts": 0, "responses_with_usage": 0, "responses_without_usage": 0}),
            (
                "s09_legacy_gap",
                {"http_attempts": 2, "responses_with_usage": 1, "responses_without_usage": 0} | _SUCCESS,
            ),
        ):
            await repo.persist_terminal_segment(
                row=ChildSegmentGeneration(
                    child_profile_id=seed.child_id,
                    generation_id=generation.generation_id,
                    section_key=key,
                    status="failed",
                    prompt_version="historical-test",
                    model=model_ref(_MODEL),
                    diagnostics={"provider": "deepseek", "provider_usage": usage, "output": _MARKER},
                )
            )
        await db.commit()
    end = datetime.now(UTC) + timedelta(minutes=1)
    authority = await _authority(s09_engine)
    assert _MARKER in authority["child_segment_generations"]
    async with s09_engine.connect() as conn:
        # The app feature was disabled while retaining Child's source diagnostics.
        before = await read_transport_costs(conn, start=start, end=end, delivered_reports=0)
        assert before.total_attempts == 0 and before.usage_coverage.ratio is None
        retained_query = select(ChildSegmentGeneration.id, ChildSegmentGeneration.diagnostics).where(
            ChildSegmentGeneration.generation_id == generation.generation_id,
            ChildSegmentGeneration.status == "ready",
        )
        retained = (await conn.execute(retained_query)).mappings().all()
        (retried,) = [row for row in retained if row.diagnostics["provider_usage"]["http_attempts"] == 2]
        assert retried.diagnostics["provider_usage"] == {
            "http_attempts": 2,
            "responses_with_usage": 2,
            "responses_without_usage": 0,
            "prompt_tokens": 8,
            "completion_tokens": 4,
            "total_tokens": 12,
        }
        assert _MARKER not in repr(retried.diagnostics)
    plan_result = await _operator_run(s09_engine, start=start, end=end)
    assert plan_result.eligible_sections == provider.calls + 4
    assert plan_result.sections_without_attempt_evidence == 2
    assert plan_result.failed_sections == 5
    assert plan_result.observed_attempts == provider.calls + 3
    assert plan_result.provider_usage_responses == provider.calls + 2
    assert plan_result.unknown_usage_attempts == 1
    assert plan_result.planned_inserts == plan_result.eligible_sections
    assert plan_result.inserted == plan_result.already_projected == 0
    async with s09_engine.connect() as conn:
        await backfill_child_usage(conn, start=start, end=end, expected_database=_DATABASE)
        with pytest.raises(DBAPIError, match="read-only transaction"):
            await conn.execute(text("DELETE FROM child_segment_generations WHERE FALSE"))
    with pytest.raises(ValueError, match="row limit exceeded"):
        await _operator_run(s09_engine, start=start, end=end, max_rows=1)
    with pytest.raises(ValueError, match="plan changed"):
        await _operator_run(s09_engine, start=start, end=end, digest="0" * 64)
    with pytest.raises(ValueError, match="plan changed"):
        await _operator_run(s09_engine, start=start, end=end + timedelta(seconds=1), digest=plan_result.plan_digest)
    async with s09_engine.connect() as conn:
        assert await conn.scalar(select(func.count()).select_from(child_usage_projection)) == 0
    first, second = await asyncio.gather(
        *(_operator_run(s09_engine, start=start, end=end, digest=plan_result.plan_digest) for _ in range(2))
    )
    assert sorted([first.inserted, second.inserted]) == [0, plan_result.eligible_sections]
    replay = await _operator_run(s09_engine, start=start, end=end, digest=plan_result.plan_digest)
    assert replay.inserted == 0 and replay.already_projected == plan_result.eligible_sections
    assert _MARKER not in json.dumps(asdict(replay))
    async with s09_engine.connect() as conn:
        projected = list((await conn.execute(select(child_usage_projection))).mappings())
        assert len(projected) == plan_result.eligible_sections
        assert _MARKER not in repr(projected)
        attempt_counts = sorted(row.http_attempts for row in projected if row.http_attempts is not None)
        assert attempt_counts == [0] + [1] * (provider.calls - 1) + [2, 2]
        (new_projection,) = [row for row in projected if row.segment_id == retried.id]
        assert new_projection.section_outcome == "ready"
        assert (new_projection.responses_with_usage, new_projection.total_tokens) == (2, 12)
        (legacy_projection,) = [row for row in projected if row.http_attempts == 2 and row.section_outcome == "failed"]
        assert (legacy_projection.responses_with_usage, legacy_projection.total_tokens) == (1, 9)
    assert await _authority(s09_engine) == authority


@respx.mock
async def test_attempt_persistence_exact_costs_and_migration_guards(
    s09_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Redirect only analytics DB to the fixture; actual adapter requests are mocked.
    monkeypatch.setattr("app.infrastructure.database.engine", s09_engine)
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    route = respx.post("https://api.deepseek.com/chat/completions").mock(
        side_effect=[
            httpx.Response(429, json={"usage": _OBSERVED | {"details": _MARKER}, "output": _MARKER}),
            httpx.ReadTimeout(_MARKER),
        ]
    )
    start = datetime.now(UTC) - timedelta(seconds=1)
    provider = DeepSeekProvider(api_key=_MARKER, model=_MODEL, timeout_seconds=2, max_retries=0)
    req: Any = _Input()
    for error in (LLMProviderUnavailableError, LLMTimeoutError):
        with pytest.raises(error):
            await provider.generate_structured(prompt=_MARKER, narrative_input=req, schema=_Output)
    assert route.call_count == 2
    async with s09_engine.begin() as connection:
        rows = list((await connection.execute(select(transport_usage))).mappings())
        assert len(rows) == 2
        assert _MARKER not in repr(rows)
        assert {row.outcome: row.total_tokens for row in rows} == {"failed": 12, "unknown": None}
        assert all(row.rate_version is None and row.model_ref == model_ref(_MODEL) for row in rows)
        rate = PinnedRate(
            "deepseek", model_ref(_MODEL), "test-rate-v1", "USD", start, Decimal("1E-38"), Decimal("2.5000"), "uniform"
        )
        facts = (
            TransportEvidence(
                start,
                "deepseek",
                model_ref(_MODEL),
                Attempt(
                    uuid4(),
                    "failed",
                    TokenUsage(1_000_000, 0, 1_000_000, "token_estimate"),
                    rate,
                ),
            ),
            TransportEvidence(
                start,
                "deepseek",
                model_ref(_MODEL),
                Attempt(
                    uuid4(),
                    "succeeded",
                    TokenUsage(0, 1_000_000, 1_000_000, "provider"),
                    replace(rate, currency="RUB"),
                ),
            ),
        )
        for fact in facts:
            await record_transport_evidence(connection, fact)
            await record_transport_evidence(connection, fact)
        with pytest.raises(ValueError, match="does not match"):
            replace(facts[0], model=model_ref("other"))
        with pytest.raises(ValueError, match="conflicting provider attempt"):
            await record_transport_evidence(connection, replace(facts[0], attempt=replace(facts[0].attempt, rate=None)))
    async with s09_engine.connect() as connection:
        summary = await read_transport_costs(
            connection, start=start, end=datetime.now(UTC) + timedelta(seconds=1), delivered_reports=1
        )
        assert summary.total_attempts == 4
        assert (summary.observed_usage_attempts, summary.estimated_usage_attempts, summary.missing_usage_attempts) == (
            2,
            1,
            1,
        )
        assert (summary.failed_attempts, summary.succeeded_attempts, summary.unknown_outcome_attempts) == (2, 1, 1)
        assert [(row.currency, row.known_estimated_subtotal) for row in summary.currencies] == [
            ("RUB", Decimal("2.5000")),
            ("USD", Decimal("1E-38")),
        ]
        assert all(row.complete_estimated_total is None for row in summary.currencies)
        assert all(row.per_delivered_report is None for row in summary.currencies)
        rated = [item for item in summary.attempt_costs if item.attempt.rate]
        assert {item.attempt.rate for item in rated} == {rate, replace(rate, currency="RUB")}
    for statement in (
        "UPDATE business_transport_usage SET outcome='failed'",
        "DELETE FROM business_child_usage_projection",
        "TRUNCATE business_transport_usage",
    ):
        async with s09_engine.connect() as connection:
            with pytest.raises(DBAPIError, match="usage evidence is append-only"):
                await connection.execute(text(statement))


@respx.mock
async def test_retry_aggregate_overflow_does_not_block_child_publication(
    s09_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.infrastructure.database.engine", s09_engine)
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    start = datetime.now(UTC)
    limit = 2**63 - 1
    rejected = {"prompt_tokens": limit - 10, "completion_tokens": 10, "total_tokens": limit}
    response = {"choices": [{"message": {"content": '{"ok":true}'}}], "usage": _SUCCESS}
    http_calls = 0

    def respond(_: httpx.Request) -> httpx.Response:
        nonlocal http_calls
        http_calls += 1
        if http_calls == 2:
            return httpx.Response(503, json={"usage": rejected})
        return httpx.Response(200, json=response)

    route = respx.post("https://api.deepseek.com/chat/completions").mock(side_effect=respond)
    async with async_sessionmaker(s09_engine, expire_on_commit=False)() as db:
        _, generation = await _seed_claimable_full_pipeline(db, idempotency_key="s09-overflow")
        provider = _ChildOverFakeTransport()
        provider.reject_first_section = False
        claim = await ChildRepository(db).claim_generation(
            generation_id=generation.generation_id, task_id="s09-overflow", now=NOW, lease_duration=timedelta(minutes=5)
        )
        assert claim is not None
        await db.commit()
        result = await run_claimed_full_generation(db, claim=claim, provider=provider, now=NOW)
        assert result.status == "ready"
        assert result.report_id is not None
    assert route.call_count == provider.calls + 1
    end = datetime.now(UTC)

    async with s09_engine.connect() as conn:
        published = (
            await conn.execute(
                select(ChildGeneration.status, ChildGeneration.report_id, ChildGeneration.pending_publication).where(
                    ChildGeneration.generation_id == generation.generation_id
                )
            )
        ).one()
        assert published == ("ready", result.report_id, None)
        assembly = (
            await conn.execute(
                select(ChildReportAssembly.status, ChildReportAssembly.payload, ChildReportAssembly.report_id).where(
                    ChildReportAssembly.generation_id == generation.generation_id
                )
            )
        ).one()
        assert assembly.report_id == result.report_id
        assert assembly.status == assembly.payload["status"] == "ready"
        segments = (
            await conn.execute(
                select(
                    ChildSegmentGeneration.id, ChildSegmentGeneration.status, ChildSegmentGeneration.diagnostics
                ).where(ChildSegmentGeneration.generation_id == generation.generation_id)
            )
        ).all()
        (retried,) = [row for row in segments if row.diagnostics.get("provider_usage", {}).get("http_attempts") == 2]
        assert retried.status == "ready"
        assert retried.diagnostics["provider_usage"] == {
            "http_attempts": 2,
            "responses_with_usage": 2,
            "responses_without_usage": 0,
            "aggregate_tokens_overflow": 1,
        }
        facts = (
            await conn.execute(
                select(transport_usage)
                .where(transport_usage.c.occurred_at >= start, transport_usage.c.occurred_at < end)
                .order_by(transport_usage.c.occurred_at)
            )
        ).all()
        assert len(facts) == route.call_count
        assert facts[1].attempt_id != facts[2].attempt_id
        assert [(fact.outcome, fact.input_tokens, fact.output_tokens, fact.total_tokens) for fact in facts[1:3]] == [
            ("failed", limit - 10, 10, limit),
            ("succeeded", 7, 2, 9),
        ]

    preview = await _operator_run(s09_engine, start=start, end=end)
    assert preview.observed_attempts == preview.provider_usage_responses == route.call_count
    assert preview.unknown_usage_attempts == 0
    await _operator_run(s09_engine, start=start, end=end, digest=preview.plan_digest)
    async with s09_engine.connect() as conn:
        projected = (
            await conn.execute(select(child_usage_projection).where(child_usage_projection.c.segment_id == retried.id))
        ).one()
        assert projected.section_outcome == "ready"
        assert (projected.http_attempts, projected.responses_with_usage, projected.responses_without_usage) == (2, 2, 0)
        assert projected.prompt_tokens is projected.completion_tokens is projected.total_tokens is None
        assert projected.prompt_cache_hit_tokens is projected.prompt_cache_miss_tokens is None
