"""Real Beat jobs for bounded internal business operations only."""

from app.config import settings
from app.infrastructure.celery_async import run_async_in_worker
from app.infrastructure.database import async_session_factory
from app.modules.analytics.operations import create_daily_digest, evaluate_business_alerts, project_business_events
from workers.celery_app import app


async def _project() -> int:
    async with async_session_factory.begin() as session:
        return await project_business_events(session)


async def _evaluate() -> dict[str, object]:
    async with async_session_factory.begin() as session:
        alerts = await evaluate_business_alerts(session)
    async with async_session_factory.begin() as session:
        digest_created = await create_daily_digest(session)
    return {"alert_changes": list(alerts), "digest_created": digest_created}


@app.task(  # type: ignore[untyped-decorator]
    name="analytics.project_business_events", ignore_result=False, soft_time_limit=45, time_limit=55
)
def project_business_events_task() -> int:
    if not settings.BUSINESS_MONITORING_ENABLED:
        return 0
    return run_async_in_worker(_project())


@app.task(  # type: ignore[untyped-decorator]
    name="analytics.evaluate_business_operations", ignore_result=False, soft_time_limit=45, time_limit=55
)
def evaluate_business_operations_task() -> dict[str, object]:
    if not settings.BUSINESS_MONITORING_ENABLED:
        return {"alert_changes": [], "digest_created": False}
    return run_async_in_worker(_evaluate())
