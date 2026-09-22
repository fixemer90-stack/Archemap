"""Celery task package imports.

Import task modules so Celery autodiscovery against `workers.tasks`
registers concrete task definitions.
"""

from workers.tasks import astrotype_v2, career, notifications, reconciliation, renewals, reports

__all__ = ["astrotype_v2", "career", "notifications", "reconciliation", "renewals", "reports"]
