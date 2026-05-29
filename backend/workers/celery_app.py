"""Celery worker application configuration."""

from __future__ import annotations

from celery import Celery

from app.config import settings

app = Celery(
    "archemap_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    task_soft_time_limit=300,
    task_time_limit=600,
    beat_schedule={
        "check-subscription-renewals": {
            "task": "workers.tasks.renewals.check_and_renew_subscriptions",
            "schedule": 3600.0,  # every hour
        },
        "run-reconciliation": {
            "task": "workers.tasks.reconciliation.run_payment_reconciliation",
            "schedule": 86400.0,  # daily
        },
    },
)

app.autodiscover_tasks(["workers.tasks"])
