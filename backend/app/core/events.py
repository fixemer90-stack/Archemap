"""Outbox event publisher placeholder.

Integrates with the Transactional Outbox pattern to reliably publish
domain events to a message broker (Redis Streams / Kafka / RabbitMQ).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    event_type: str = ""
    aggregate_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


async def publish_event(event: DomainEvent) -> None:
    """Persist event to the outbox table and/or push to broker.

    TODO: implement with SQLAlchemy outbox table + background dispatcher.
    """
    logger.info("event_published", event_type=event.event_type, aggregate_id=event.aggregate_id)
