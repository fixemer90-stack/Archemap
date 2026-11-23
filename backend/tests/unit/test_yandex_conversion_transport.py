"""Verify the exact offline wire contract without network access."""

from datetime import UTC, datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser

import httpx
import pytest
from pydantic import SecretStr

from app.modules.analytics.yandex_transport import MetricaDestination, MetricaTransport, UploadPhase, UploadReceipt


async def test_offline_upload_sends_only_three_columns_and_reads_status() -> None:
    methods: list[str] = []

    async def provider(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        assert request.url.host == "api-metrika.yandex.net"
        assert request.headers["Authorization"] == "OAuth test-secret"
        assert not request.url.query
        base = "/management/v1/counter/123/offline_conversions"
        if request.method == "POST":
            assert request.url.path == base + "/upload"
            body = await request.aread()
            message = BytesParser(policy=policy.default).parsebytes(
                f"Content-Type: {request.headers['content-type']}\r\n\r\n".encode() + body
            )
            parts = list(message.iter_parts())
            assert len(parts) == 1
            assert parts[0].get_param("name", header="content-disposition") == "file"
            assert parts[0].get_filename() == "conversion.csv"
            assert parts[0].get_payload(decode=True) == (
                b"ClientId,Target,DateTime\r\n001234567890123456,plus_initial_purchase,1767225600\r\n"
            )
            return httpx.Response(200, json={"uploading": {"id": 73, "status": "UPLOADED"}})
        assert request.url.path == base + "/uploading/73"
        assert not await request.aread()
        return httpx.Response(200, json={"uploading": {"id": 73, "status": "PROCESSED"}})

    config = MetricaDestination(123, "plus_initial_purchase", SecretStr("test-secret"))
    transport = MetricaTransport(config, mock_transport=httpx.MockTransport(provider))
    original = datetime(2026, 1, 1, 3, 0, 0, 999999, tzinfo=timezone(timedelta(hours=3)))
    assert await transport.upload("001234567890123456", original) == UploadReceipt(73, UploadPhase.UPLOADED)
    assert await transport.read_status(73) == UploadReceipt(73, UploadPhase.PROCESSED)
    assert methods == ["POST", "GET"]
    assert "test-secret" not in repr(config)


@pytest.mark.parametrize("outcome", ["timeout", "redirect", "server-error", "invalid-json", "invalid-id"])
async def test_ambiguous_post_is_never_retried(outcome: str) -> None:
    attempts = 0

    def provider(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if outcome == "timeout":
            raise httpx.ReadTimeout("provider-details-not-for-logs", request=request)
        if outcome == "redirect":
            return httpx.Response(307, headers={"location": "https://example.invalid/"})
        if outcome == "server-error":
            return httpx.Response(500)
        if outcome == "invalid-json":
            return httpx.Response(200, content=b"not JSON")
        return httpx.Response(200, json={"uploading": {"id": True, "status": "UPLOADED"}})

    transport = MetricaTransport(
        MetricaDestination(123, "plus_initial_purchase", SecretStr("test-secret")),
        mock_transport=httpx.MockTransport(provider),
    )
    assert await transport.upload("100", datetime(2026, 1, 1, tzinfo=UTC)) is None
    assert attempts == 1
