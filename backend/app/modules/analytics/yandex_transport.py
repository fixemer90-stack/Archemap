"""Single-row Yandex Metrica offline import; no redirects or transport retries."""

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

import httpx
from pydantic import SecretStr

CLIENT_ID = re.compile(r"[0-9]{1,32}", re.ASCII)
MAX_UPLOAD_ID = 2**63 - 1


class UploadPhase(StrEnum):
    PREPARED = "PREPARED"
    UPLOADED = "UPLOADED"
    EXPORTED = "EXPORTED"
    MATCHED = "MATCHED"
    PROCESSED = "PROCESSED"
    LINKAGE_FAILURE = "LINKAGE_FAILURE"


@dataclass(frozen=True, slots=True)
class MetricaDestination:
    counter_id: int
    target: str
    token: SecretStr = field(repr=False)

    def __post_init__(self) -> None:
        if not (
            type(self.counter_id) is int
            and 0 < self.counter_id <= MAX_UPLOAD_ID
            and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}", self.target)
            and re.fullmatch(r"[A-Za-z0-9_.-]{1,2048}", self.token.get_secret_value())
        ):
            raise ValueError("invalid offline conversion destination")


@dataclass(frozen=True, slots=True)
class UploadReceipt:
    upload_id: int
    phase: UploadPhase | None


def _upload_receipt(payload: object) -> UploadReceipt | None:
    entity = payload.get("uploading") if isinstance(payload, dict) else None
    if not isinstance(entity, dict):
        return None
    upload_id = entity.get("id")
    if type(upload_id) is not int or not 0 < upload_id <= MAX_UPLOAD_ID:
        return None
    status = entity.get("status")
    try:
        phase = UploadPhase(status) if isinstance(status, str) else None
    except ValueError:
        phase = None
    return UploadReceipt(upload_id, phase)


class MetricaTransport:
    def __init__(self, destination: MetricaDestination, *, mock_transport: httpx.MockTransport | None = None) -> None:
        self._destination = destination
        self._mock_transport = mock_transport

    async def upload(self, client_id: str, occurred_at: datetime) -> UploadReceipt | None:
        if not CLIENT_ID.fullmatch(client_id) or occurred_at.utcoffset() is None:
            raise ValueError("invalid offline conversion row")
        delta = occurred_at - datetime(1970, 1, 1, tzinfo=UTC)
        timestamp = delta.days * 86400 + delta.seconds
        if timestamp <= 0:
            raise ValueError("invalid offline conversion timestamp")
        # Delimiter-safe fields are validated above and at destination construction.
        payload = f"ClientId,Target,DateTime\r\n{client_id},{self._destination.target},{timestamp}\r\n".encode("ascii")
        return await self._request("POST", "upload", payload)

    async def read_status(self, upload_id: int) -> UploadReceipt | None:
        if type(upload_id) is not int or not 0 < upload_id <= MAX_UPLOAD_ID:
            raise ValueError("invalid offline upload ID")
        result = await self._request("GET", f"uploading/{upload_id}")
        return result if result is not None and result.upload_id == upload_id else None

    async def _request(
        self, method: Literal["POST", "GET"], path: str, payload: bytes | None = None
    ) -> UploadReceipt | None:
        url = f"https://api-metrika.yandex.net/management/v1/counter/{self._destination.counter_id}/offline_conversions/{path}"
        files = {"file": ("conversion.csv", payload, "text/csv")} if payload is not None else None
        try:
            async with (
                httpx.AsyncClient(
                    transport=self._mock_transport,
                    timeout=10.0,
                    follow_redirects=False,
                    trust_env=False,
                    headers={"Authorization": f"OAuth {self._destination.token.get_secret_value()}"},
                ) as client,
                client.stream(method, url, files=files) as response,
            ):
                if response.status_code == 200:
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(body) + len(chunk) > 16_384:
                            return None
                        body.extend(chunk)
                    return _upload_receipt(json.loads(body))
        except (httpx.HTTPError, ValueError, RecursionError):
            pass  # Do not retain provider bodies, URLs from errors, or exception text.
        return None
