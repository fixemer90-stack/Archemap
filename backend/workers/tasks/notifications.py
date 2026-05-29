"""Notification dispatch background tasks."""

from __future__ import annotations

import structlog

from workers.celery_app import app

logger = structlog.get_logger()


@app.task(name="workers.tasks.notifications.send_notification")
def send_notification(user_id: str, channel: str, template: str, context: dict | None = None) -> bool:
    """Send a notification to a user via the specified channel.

    Channels: email, push, in_app.
    TODO: integrate with email service / push provider.
    """
    logger.info("notification_sent", user_id=user_id, channel=channel, template=template)
    return True


@app.task(name="workers.tasks.notifications.send_bulk_notification")
def send_bulk_notification(user_ids: list[str], channel: str, template: str, context: dict | None = None) -> int:
    """Send notifications to multiple users."""
    count = 0
    for uid in user_ids:
        send_notification(uid, channel, template, context)
        count += 1
    logger.info("bulk_notification_sent", count=count, channel=channel)
    return count
