"""Allowlisted E23 operator notices and a single bounded Telegram Bot API call."""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from pydantic import SecretStr

from app.modules.analytics.operations import MOSCOW, IncidentCode, moscow_day_bounds
from app.modules.analytics.operations_models import BusinessOperatorMessage
from app.modules.analytics.schemas import EventType, Mode, Product

MAX_TEXT = 3_900
MAX_RESPONSE_BYTES = 16_384
HTTP_DEADLINE = 5
_INCIDENTS = {code.value for code in IncidentCode}
_EVENTS = {event.value for event in EventType}
_MODES = {mode.value for mode in Mode}
_PRODUCTS = {product.value for product in Product}
_MAX_BIGINT = 2**63 - 1


def _digest(payload: dict[str, object]) -> str | None:
    if (
        payload.keys() != {"timezone", "from_utc", "to_utc", "projector_succeeded_at", "coverage", "counts"}
        or payload["timezone"] != MOSCOW.key
        or payload["coverage"] != "recorded_facts_only"
    ):
        return None
    start, end, heartbeat = (payload[key] for key in ("from_utc", "to_utc", "projector_succeeded_at"))
    if not isinstance(start, str) or not isinstance(end, str) or not isinstance(heartbeat, str):
        return None
    try:
        if any(len(value) > 40 for value in (start, end, heartbeat)):
            return None
        start_at, end_at, succeeded_at = map(datetime.fromisoformat, (start, end, heartbeat))
        if start_at.utcoffset() is None or end_at.utcoffset() is None or succeeded_at.utcoffset() is None:
            return None
        business_day = start_at.astimezone(MOSCOW).date()
        if (start_at, end_at) != moscow_day_bounds(business_day) or succeeded_at < end_at:
            return None
    except (ValueError, OverflowError):
        return None

    rows = payload["counts"]
    if not isinstance(rows, list) or len(rows) > len(_EVENTS) * len(_MODES) * (len(_PRODUCTS) + 1):
        return None
    totals: dict[tuple[str, str], int] = {}
    buckets: set[tuple[str, str, str | None]] = set()
    for row in rows:
        if not isinstance(row, dict) or row.keys() != {"event_type", "mode", "product", "count"}:
            return None
        event, mode, product, count = (row[key] for key in ("event_type", "mode", "product", "count"))
        if (
            not isinstance(event, str)
            or event not in _EVENTS
            or not isinstance(mode, str)
            or mode not in _MODES
            or (product is not None and (not isinstance(product, str) or product not in _PRODUCTS))
            or type(count) is not int
            or not 0 < count <= _MAX_BIGINT
            or (mode, event, product) in buckets
        ):
            return None
        buckets.add((mode, event, product))
        totals[mode, event] = totals.get((mode, event), 0) + count

    lines = [f"Business digest: {business_day.isoformat()} (Europe/Moscow)", "Recorded events only; all products"]
    lines.extend(f"{mode} / {event}: {count}" for (mode, event), count in sorted(totals.items()))
    if not totals:
        lines.append("No recorded events")
    return "\n".join(lines)


def render_operator_message(message: BusinessOperatorMessage) -> str | None:
    """Render only registered codes, bounded counts, and the Moscow date; never raw JSON."""
    payload = message.payload
    if not isinstance(payload, dict):
        return None
    if (message.code, message.kind) == ("daily_business_digest", "digest"):
        result = _digest(payload)
        return result if result and len(result) <= MAX_TEXT else None
    if not payload and message.code in _INCIDENTS and message.kind in {"opened", "reminder", "resolved"}:
        return f"Business alert: {message.code} ({message.kind})"
    return None


@dataclass(frozen=True, slots=True)
class TelegramDestination:
    token: SecretStr = field(repr=False)
    chat_id: int = field(repr=False)

    def __post_init__(self) -> None:
        if not (
            re.fullmatch(r"[0-9]{1,20}:[A-Za-z0-9_-]{1,128}", self.token.get_secret_value(), re.ASCII)
            and type(self.chat_id) is int
            and 0 < abs(self.chat_id) < 2**52
        ):
            raise ValueError("invalid Telegram destination")


def _receipt_matches(data: object, chat_id: int) -> bool:
    if not isinstance(data, dict) or data.get("ok") is not True:
        return False
    result = data.get("result")
    if not isinstance(result, dict):
        return False
    message_id, chat = result.get("message_id"), result.get("chat")
    return (
        type(message_id) is int
        and 0 < message_id <= _MAX_BIGINT
        and isinstance(chat, dict)
        and type(chat.get("id")) is int
        and chat["id"] == chat_id
    )


class TelegramTransport:
    def __init__(self, destination: TelegramDestination, *, mock_transport: httpx.MockTransport | None = None) -> None:
        self._destination = destination
        self._mock_transport = mock_transport

    async def send(self, content: str) -> bool:
        if not 0 < len(content) <= MAX_TEXT or not content.isascii():
            return False
        # Never use an environment proxy or follow a redirect carrying the bot token.
        url = f"https://api.telegram.org/bot{self._destination.token.get_secret_value()}/sendMessage"
        payload = {"chat_id": self._destination.chat_id, "text": content, "link_preview_options": {"is_disabled": True}}
        try:
            async with (
                asyncio.timeout(HTTP_DEADLINE),
                httpx.AsyncClient(
                    transport=self._mock_transport,
                    timeout=HTTP_DEADLINE,
                    follow_redirects=False,
                    trust_env=False,
                    headers={"Accept-Encoding": "identity"},
                ) as client,
                client.stream("POST", url, json=payload) as response,
            ):
                if response.status_code != 200 or response.headers.get("Content-Encoding", "identity") != "identity":
                    return False
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                        return False
                    body.extend(chunk)
                return _receipt_matches(json.loads(body), self._destination.chat_id)
        except (TimeoutError, httpx.HTTPError, ValueError, RecursionError):
            return False  # No response bodies, URLs, or exception details leave the adapter.
