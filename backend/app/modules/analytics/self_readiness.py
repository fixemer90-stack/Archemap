"""Conservative Self publication bounds; never reconstruct intent on replay."""

import asyncio
from uuid import UUID

import structlog
from sqlalchemy import func, insert, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.modules.analytics.models import SelfReadinessEvidence

logger = structlog.get_logger()

_READ_TIMEOUTS = text("""
    SELECT name, setting::int FROM pg_settings WHERE name IN ('statement_timeout', 'lock_timeout')
""")
_SET_TIMEOUTS = text("""
    SELECT set_config('statement_timeout', :statement_timeout, true),
           set_config('lock_timeout', :lock_timeout, true)
""")


async def stage_self_readiness(
    db: AsyncSession, *, event_id: UUID, report_id: UUID, owner_id: UUID, generation_id: UUID
) -> None:
    """Stage only alongside an original, still uncommitted foundation and fact."""
    try:
        # The caller has already flushed business writes. A proof-only failure
        # must not roll back the foundation, event, or outbox in the outer unit.
        async with db.begin_nested():
            caller = dict((await db.execute(_READ_TIMEOUTS)).tuples().all())
            await db.execute(
                _SET_TIMEOUTS,
                {
                    "statement_timeout": f"{min(caller['statement_timeout'] or 1000, 1000)}ms",
                    "lock_timeout": f"{min(caller['lock_timeout'] or 500, 500)}ms",
                },
            )
            await db.execute(text("LOCK TABLE business_self_readiness_evidence IN ROW EXCLUSIVE MODE NOWAIT"))
            await db.execute(
                insert(SelfReadinessEvidence).values(
                    event_id=event_id,
                    report_id=report_id,
                    owner_id=owner_id,
                    generation_id=generation_id,
                    publish_not_before=func.clock_timestamp(),
                )
            )
            # RELEASE keeps SET LOCAL changes; rollback to the savepoint restores them automatically.
            await db.execute(_SET_TIMEOUTS, {name: f"{value}ms" for name, value in caller.items()})
    except Exception:
        logger.warning("self_readiness_intent_unavailable")


_OBSERVE = """
    WITH visible AS MATERIALIZED (
        SELECT p.event_id
          FROM business_self_readiness_evidence p
          JOIN business_events e ON e.id = p.event_id AND e.entity_id = p.report_id AND e.subject_id = p.owner_id
          JOIN astrotype_v2_natal_reports r ON r.id = p.report_id AND r.generation_id = p.generation_id
          JOIN astrotype_v2_natal_charts c ON c.id = r.chart_id AND c.user_id = p.owner_id
          JOIN astrotype_v2_natal_report_generations g ON g.generation_id = p.generation_id AND g.report_id = r.id
              AND g.profile_id = c.profile_id AND g.user_id = p.owner_id
         WHERE p.observed_at IS NULL AND e.event_type = 'basic_report_ready' AND e.product = 'self'
           AND e.semantic_key = 'v1:basic_report_ready:' || r.id::text || ':-'
           AND jsonb_typeof(r.deterministic_payload) = 'object' AND r.deterministic_payload <> '{{}}'::jsonb
           {scope}
         ORDER BY p.publish_not_before, p.event_id LIMIT 100
         FOR UPDATE OF p SKIP LOCKED
    )
    UPDATE business_self_readiness_evidence p
       SET observed_at = clock_timestamp()
      FROM visible WHERE p.event_id = visible.event_id AND p.observed_at IS NULL
    RETURNING p.event_id
"""
_OBSERVE_PENDING = text(_OBSERVE.format(scope=""))
_OBSERVE_ONE = text(_OBSERVE.format(scope="AND p.event_id = :event_id"))


async def observe_self_readiness(sessions: async_sessionmaker[AsyncSession], *, event_id: UUID | None = None) -> int:
    """Record the first durable observation of already committed owner-bound intent.

    No report status, business fact, or provider work is changed. A recovery
    observation uses its actual DB time and cannot backdate a lost observation.
    """
    if not settings.BUSINESS_MONITORING_ENABLED:
        return 0
    try:
        async with asyncio.timeout(2), sessions.begin() as db:
            await db.execute(text("SET LOCAL statement_timeout = '1s'"))
            await db.execute(text("SET LOCAL synchronous_commit = on"))
            ids = (
                await db.scalars(_OBSERVE_PENDING)
                if event_id is None
                else await db.scalars(_OBSERVE_ONE, {"event_id": event_id})
            )
            return len(ids.all())
    except Exception:
        logger.warning("self_readiness_observation_unavailable")
        return 0
