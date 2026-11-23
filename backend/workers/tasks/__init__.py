"""Celery task package imports.

Import task modules so Celery autodiscovery against `workers.tasks`
registers concrete task definitions.
"""

from workers.tasks import (
    astrotype_v2,
    business_operations,
    career,
    child,
    notifications,
    profile_refinement,
    reconciliation,
    renewals,
    reports,
)

__all__ = [
    "astrotype_v2",
    "business_operations",
    "career",
    "child",
    "notifications",
    "profile_refinement",
    "reconciliation",
    "renewals",
    "reports",
]
