"""Celery worker application configuration."""

from __future__ import annotations

from celery import Celery

from app.config import settings
from app.infrastructure.observability import configure_metrics


def configure_worker_observability() -> bool:
    """Export worker-side Career metrics through the configured OTLP endpoint."""

    return configure_metrics(
        endpoint=settings.OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
        service_name=f"{settings.OTEL_SERVICE_NAME}-worker",
    )


configure_worker_observability()

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
    task_routes={
        "profiles.monitor_birth_data_refinements": {"queue": "birth-data-monitor"},
    },
    beat_schedule={
        "check-subscription-renewals": {
            "task": "workers.tasks.renewals.check_and_renew_subscriptions",
            "schedule": 3600.0,  # every hour
        },
        "run-reconciliation": {
            "task": "workers.tasks.reconciliation.run_payment_reconciliation",
            "schedule": 86400.0,  # daily
        },
        "monitor-career-pipeline": {
            "task": "career.monitor_pipeline",
            "schedule": 300.0,
        },
        "dispatch-birth-data-refinements": {
            "task": "profiles.dispatch_birth_data_refinements",
            "schedule": 60.0,
        },
        "monitor-birth-data-refinements": {
            "task": "profiles.monitor_birth_data_refinements",
            "schedule": float(settings.BIRTH_DATA_REFINEMENT_MONITOR_INTERVAL_SECONDS),
        },
    },
)

app.autodiscover_tasks(["workers.tasks"])
