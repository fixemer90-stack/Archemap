"""DB-independent outcome codes for the standalone business watchdog."""

from enum import StrEnum


class WatchdogStatus(StrEnum):
    HEALTHY = "healthy"
    STALE = "stale"
    BUSY = "busy"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"
