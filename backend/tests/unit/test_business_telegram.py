"""Telegram HTTP and payload contracts run without a network connection."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from app.config import settings
from app.modules.analytics import telegram_transport
from app.modules.analytics.operations_models import BusinessOperatorMessage
from app.modules.analytics.telegram_delivery import DeliveryStatus, _destination_from_environment, run
from app.modules.analytics.telegram_transport import TelegramDestination, TelegramTransport, render_operator_message

NOW = datetime(2026, 6, 1, 7, tzinfo=UTC)
TOKEN = "123456:mock_token"
DEST = TelegramDestination(SecretStr(TOKEN), -100123)


@pytest.mark.parametrize(
    ("status", "body", "accepted"),
    [
        (200, {"ok": True, "result": {"message_id": 5, "chat": {"id": -100123}}}, True),
        (200, {"ok": True, "result": {"message_id": 5, "chat": {"id": -100124}}}, False),
        (200, {"ok": True, "result": {"message_id": True, "chat": {"id": -100123}}}, False),
        (200, {"ok": 1, "result": {"message_id": 5, "chat": {"id": -100123}}}, False),
        (200, {"ok": False}, False),
        (200, "oversize" * 4_000, False),
        (302, {"ok": False}, False),
        (429, {"ok": False, "parameters": {"retry_after": 1}}, False),
        (503, {"ok": False}, False),
    ],
)
async def test_telegram_requires_exact_receipt_without_redirect_or_retry(
    status: int, body: object, accepted: bool
) -> None:
    calls = []

    def receive(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(status, json=body, headers={"Location": "https://wrong.invalid"})

    transport = TelegramTransport(DEST, mock_transport=httpx.MockTransport(receive))
    assert await transport.send("bounded notice") is accepted
    assert len(calls) == 1
    assert calls[0].method == "POST"
    assert str(calls[0].url) == f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    assert json.loads(calls[0].content) == {
        "chat_id": -100123,
        "text": "bounded notice",
        "link_preview_options": {"is_disabled": True},
    }


async def test_telegram_transport_timeout_has_no_retry() -> None:
    attempts = 0

    def receive(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("provider secret", request=request)

    transport = TelegramTransport(DEST, mock_transport=httpx.MockTransport(receive))
    assert not await transport.send("bounded notice")
    assert attempts == 1


async def test_telegram_wall_deadline_caps_a_waiting_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(telegram_transport, "HTTP_DEADLINE", 0.05)
    attempts = 0

    async def receive(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        await asyncio.Future[None]()
        raise AssertionError("waiting transport should be cancelled")

    transport = TelegramTransport(DEST, mock_transport=httpx.MockTransport(receive))
    assert not await asyncio.wait_for(transport.send("bounded notice"), timeout=0.5)
    assert attempts == 1


@pytest.mark.parametrize(("monitoring", "alerts"), [(False, False), (True, False), (False, True)])
async def test_disabled_sender_does_not_load_credentials(
    monkeypatch: pytest.MonkeyPatch, monitoring: bool, alerts: bool
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", monitoring)
    monkeypatch.setattr(settings, "BUSINESS_ALERTS_ENABLED", alerts)
    monkeypatch.setenv("DATABASE_URL", "unused")

    def credential_lookup() -> None:
        pytest.fail("disabled sender must not inspect credentials")

    monkeypatch.setattr("app.modules.analytics.telegram_delivery._destination_from_environment", credential_lookup)
    assert await run() is DeliveryStatus.DISABLED


def test_sender_requires_an_aware_cutover_and_private_credential_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    monkeypatch.setenv("BUSINESS_TELEGRAM_ACTIVE_SINCE", NOW.isoformat())
    assert _destination_from_environment() is None
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(tmp_path))
    (tmp_path / "telegram_chat_id").write_text("-100123\n", encoding="ascii")
    (tmp_path / "telegram_token").write_text(f"{TOKEN}\n", encoding="ascii")
    assert _destination_from_environment() == (DEST, NOW)
    monkeypatch.setenv("BUSINESS_TELEGRAM_ACTIVE_SINCE", NOW.replace(tzinfo=None).isoformat())
    assert _destination_from_environment() is None


def test_operator_message_renders_only_allowlisted_aggregate_facts() -> None:
    digest = BusinessOperatorMessage(
        message_key="do not export key",
        kind="digest",
        code="daily_business_digest",
        created_at=NOW,
        payload={
            "timezone": "Europe/Moscow",
            "from_utc": "2026-05-30T21:00:00+00:00",
            "to_utc": "2026-05-31T21:00:00+00:00",
            "projector_succeeded_at": NOW.isoformat(),
            "coverage": "recorded_facts_only",
            "counts": [{"event_type": "report_ready", "mode": "test", "product": "child", "count": 2}],
        },
    )
    rendered = render_operator_message(digest)
    assert rendered is not None and "2026-05-31" in rendered and "test / report_ready: 2" in rendered
    assert "do not export key" not in rendered
    digest.payload["user_email"] = "private@example.invalid"
    assert render_operator_message(digest) is None
    del digest.payload["user_email"]
    digest.payload["counts"] = [{"event_type": "customer@example.invalid", "mode": "test", "product": None, "count": 1}]
    assert render_operator_message(digest) is None


@pytest.mark.parametrize("token", ["", "12:a/b", "12:a?b", "https://elsewhere.invalid"])
def test_telegram_rejects_invalid_token_without_printing_it(token: str) -> None:
    with pytest.raises(ValueError, match=r"^invalid Telegram destination$"):
        TelegramDestination(SecretStr(token), -100123)
    assert TOKEN not in repr(DEST) and "100123" not in repr(DEST)
