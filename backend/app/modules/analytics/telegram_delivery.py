"""One-message Telegram runner. No Celery, Redis, or automatic retransmission."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from pydantic import SecretStr
from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

if TYPE_CHECKING:
    from app.modules.analytics.telegram_transport import TelegramDestination

MAX_AGE = timedelta(days=1)
DB_DEADLINE = 8


class DeliveryStatus(StrEnum):
    IDLE = "idle"
    ACKNOWLEDGED = "acknowledged"
    INDETERMINATE = "indeterminate"
    INVALID_MESSAGE = "invalid_message"
    DISABLED = "disabled"
    MISCONFIGURED = "misconfigured"
    UNAVAILABLE = "unavailable"


class Sender(Protocol):
    async def send(self, content: str) -> bool: ...


async def deliver_once(
    sessions: async_sessionmaker[AsyncSession], sender: Sender, *, active_since: datetime
) -> DeliveryStatus:
    """Make at most one attempt. A committed fence survives every ambiguous outcome."""
    from app.modules.analytics.operations_models import BusinessOperatorMessage, BusinessTelegramDelivery
    from app.modules.analytics.telegram_transport import render_operator_message

    if active_since.utcoffset() is None:
        return DeliveryStatus.MISCONFIGURED
    async with asyncio.timeout(DB_DEADLINE), sessions.begin() as session:
        now = await session.scalar(select(func.clock_timestamp()))
        assert now is not None
        if active_since > now:
            return DeliveryStatus.IDLE
        message = await session.scalar(
            select(BusinessOperatorMessage)
            .where(
                BusinessOperatorMessage.created_at > active_since,
                BusinessOperatorMessage.created_at >= now - MAX_AGE,
                BusinessOperatorMessage.created_at <= now,
                ~select(BusinessTelegramDelivery.message_key)
                .where(BusinessTelegramDelivery.message_key == BusinessOperatorMessage.message_key)
                .exists(),
            )
            .order_by(BusinessOperatorMessage.created_at, BusinessOperatorMessage.message_key)
            .limit(1)
            .with_for_update(of=BusinessOperatorMessage, skip_locked=True)
        )
        if message is None:
            return DeliveryStatus.IDLE
        content = render_operator_message(message)
        # Even with asynchronous commit as a DB default, never send before this WAL is durable.
        await session.execute(text("SET LOCAL synchronous_commit = on"))
        key = await session.scalar(
            insert(BusinessTelegramDelivery)
            .values(
                message_key=message.message_key,
                status=DeliveryStatus.INDETERMINATE if content else DeliveryStatus.INVALID_MESSAGE,
                recorded_at=now,
            )
            .on_conflict_do_nothing(index_elements=[BusinessTelegramDelivery.message_key])
            .returning(BusinessTelegramDelivery.message_key)
        )
    if key is None:
        return DeliveryStatus.IDLE
    if content is None:
        return DeliveryStatus.INVALID_MESSAGE
    if not await sender.send(content):
        return DeliveryStatus.INDETERMINATE
    async with asyncio.timeout(DB_DEADLINE), sessions.begin() as session:
        await session.execute(text("SET LOCAL synchronous_commit = on"))
        updated = await session.scalar(
            update(BusinessTelegramDelivery)
            .where(
                BusinessTelegramDelivery.message_key == key,
                BusinessTelegramDelivery.status == DeliveryStatus.INDETERMINATE,
            )
            .values(
                status=DeliveryStatus.ACKNOWLEDGED,
                acknowledged_at=func.greatest(func.clock_timestamp(), BusinessTelegramDelivery.recorded_at),
            )
            .returning(BusinessTelegramDelivery.message_key)
        )
    return DeliveryStatus.ACKNOWLEDGED if updated is not None else DeliveryStatus.INDETERMINATE


def _destination_from_environment() -> tuple[TelegramDestination, datetime] | None:
    from app.modules.analytics.telegram_transport import TelegramDestination

    raw_since = os.environ.get("BUSINESS_TELEGRAM_ACTIVE_SINCE", "")
    credentials = os.environ.get("CREDENTIALS_DIRECTORY")
    if not credentials or not Path(credentials).is_absolute() or len(raw_since) > 40:
        return None
    try:
        start = datetime.fromisoformat(raw_since)
        if start.utcoffset() is None:
            return None
        # LoadCredential keeps recipient and bot token out of service environment/journal.
        with (Path(credentials) / "telegram_chat_id").open(encoding="ascii") as stream:
            raw_chat = stream.read(20).removesuffix("\n")
        if not re.fullmatch(r"-?[1-9][0-9]{0,15}", raw_chat, re.ASCII):
            return None
        with (Path(credentials) / "telegram_token").open(encoding="ascii") as stream:
            token = stream.read(152).removesuffix("\n")
        destination = TelegramDestination(SecretStr(token), int(raw_chat))
        return destination, start.astimezone(UTC)
    except (OSError, ValueError, OverflowError):
        return None


async def run() -> DeliveryStatus:
    try:
        from app.config import settings

        if not (settings.BUSINESS_MONITORING_ENABLED and settings.BUSINESS_ALERTS_ENABLED):
            return DeliveryStatus.DISABLED
        if not os.environ.get("DATABASE_URL"):
            return DeliveryStatus.MISCONFIGURED
        config = _destination_from_environment()
        if config is None:
            return DeliveryStatus.MISCONFIGURED
        from app.infrastructure.database import async_session_factory, engine
        from app.modules.analytics.telegram_transport import TelegramTransport

        destination, active_since = config
        try:
            return await deliver_once(async_session_factory, TelegramTransport(destination), active_since=active_since)
        finally:
            await engine.dispose()
    except Exception:
        return DeliveryStatus.UNAVAILABLE


def main() -> int:
    # The Bot API puts its token in the URL. This standalone process emits only a bounded status;
    # suppress library logs, notably httpx's default INFO request log with the full URL.
    logging.disable(logging.CRITICAL)
    status = asyncio.run(run())
    print(f"business_telegram_delivery={status}")
    return {
        DeliveryStatus.IDLE: 0,
        DeliveryStatus.ACKNOWLEDGED: 0,
        DeliveryStatus.INDETERMINATE: 1,
        DeliveryStatus.INVALID_MESSAGE: 1,
        DeliveryStatus.UNAVAILABLE: 2,
        DeliveryStatus.MISCONFIGURED: 2,
        DeliveryStatus.DISABLED: 4,
    }[status]


if __name__ == "__main__":
    raise SystemExit(main())
