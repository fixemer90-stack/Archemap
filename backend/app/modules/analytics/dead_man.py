"""Run out of band: python -m app.modules.analytics.dead_man.

Schedule independently of the app/Beat/worker/broker. A nonzero exit also
signals PostgreSQL unavailability, when no central notification can be stored.
"""

import asyncio
import logging
import os

from app.modules.analytics.watchdog_status import WatchdogStatus


async def observe() -> WatchdogStatus:
    try:
        from app.config import settings

        if not settings.BUSINESS_MONITORING_ENABLED:
            return WatchdogStatus.DISABLED
        if not os.environ.get("DATABASE_URL"):
            return WatchdogStatus.UNAVAILABLE
        from app.infrastructure.database import async_session_factory, engine
        from app.modules.analytics.operations import check_dead_man

        try:
            async with asyncio.timeout(8), async_session_factory.begin() as session:
                return await check_dead_man(session)
        finally:
            await engine.dispose()
    except Exception:
        # The observer's output must not reveal connection strings or SQL parameters.
        return WatchdogStatus.UNAVAILABLE


def main() -> int:
    logging.disable(logging.CRITICAL)
    status = asyncio.run(observe())
    print(f"business_projection_watchdog={status}")
    return {
        WatchdogStatus.HEALTHY: 0,
        WatchdogStatus.STALE: 1,
        WatchdogStatus.UNAVAILABLE: 2,
        WatchdogStatus.BUSY: 3,
        WatchdogStatus.DISABLED: 4,
    }[status]


if __name__ == "__main__":
    raise SystemExit(main())
