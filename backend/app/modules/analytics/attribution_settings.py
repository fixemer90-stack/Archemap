"""Separate, default-off attribution admission; never authorizes an external upload."""

import os
import re
from dataclasses import dataclass
from datetime import timedelta

POLICY_PATTERN = r"[A-Za-z0-9._-]{1,64}"
COUNTER_ID_PATTERN = r"[1-9][0-9]{0,18}"
MAX_COUNTER_ID = 2**63 - 1
CLIENT_ID_PATTERN = r"[0-9]{1,32}"
PENDING_SECONDS = 30 * 60


@dataclass(frozen=True, slots=True)
class AttributionPolicy:
    version: str
    retention: timedelta
    counter_id: int


def approved_attribution_policy() -> AttributionPolicy | None:
    """All four deployment values must be explicit; malformed settings fail closed."""
    if os.getenv("ANALYTICS_ATTRIBUTION_POLICY_APPROVED") != "true":
        return None
    version = os.getenv("ANALYTICS_ATTRIBUTION_POLICY_VERSION", "")
    days = os.getenv("ANALYTICS_ATTRIBUTION_RETENTION_DAYS", "")
    if not re.fullmatch(POLICY_PATTERN, version) or not re.fullmatch(r"[1-9][0-9]{0,2}", days):
        return None
    counter = os.getenv("ANALYTICS_ATTRIBUTION_COUNTER_ID", "")
    if not re.fullmatch(COUNTER_ID_PATTERN, counter) or int(counter) > MAX_COUNTER_ID or int(days) > 90:
        return None
    return AttributionPolicy(version, timedelta(days=int(days)), int(counter))
