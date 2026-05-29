"""Subscription renewal background tasks."""

from __future__ import annotations

import structlog

from workers.celery_app import app

logger = structlog.get_logger()


@app.task(name="workers.tasks.renewals.check_and_renew_subscriptions")  # type: ignore[untyped-decorator]
def check_and_renew_subscriptions() -> dict[str, int]:
    """Find subscriptions due for renewal and process them.

    TODO: query expiring subscriptions, create payment intents,
    update status on success/failure.
    """
    logger.info("renewal_check_started")
    processed = 0
    failed = 0
    # placeholder logic
    logger.info("renewal_check_completed", processed=processed, failed=failed)
    return {"processed": processed, "failed": failed}
