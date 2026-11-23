"""Bounded browser ingress. No general event, URL, owner or clock passthrough."""

import json
import secrets
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import AwareDatetime, Field, ValidationError, field_validator
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import ClientDisconnect

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.infrastructure.redis import get_redis_client
from app.modules.analytics.attribution import bind_attribution, receipt_is_fresh, revoke_attribution
from app.modules.analytics.attribution_settings import (
    CLIENT_ID_PATTERN,
    COUNTER_ID_PATTERN,
    MAX_COUNTER_ID,
    PENDING_SECONDS,
    POLICY_PATTERN,
    approved_attribution_policy,
)
from app.modules.analytics.collector_events import ReaderProduct, observe_owned_report
from app.modules.analytics.schemas import StrictModel

_MAX_BODY = 1024
_HEADERS = {"Cache-Control": "private, no-store"}
_RATE = "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],60) end; return n"
Owner = Annotated[UUID, Depends(get_current_user)]
DB = Annotated[AsyncSession, Depends(get_db, scope="function")]
Cache = Annotated[Redis, Depends(get_redis_client)]
ReceiptToken = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{43}$")]
PolicyVersion = Annotated[str, Field(pattern=rf"^{POLICY_PATTERN}$")]
SourceCounterID = Annotated[str, Field(pattern=rf"^{COUNTER_ID_PATTERN}$")]
ClientID = Annotated[str, Field(pattern=rf"^{CLIENT_ID_PATTERN}$")]


class ReportOpened(StrictModel):
    event: Literal["report_opened"]
    product: ReaderProduct
    report_id: UUID

    @field_validator("report_id", mode="before")
    @classmethod
    def canonical_report_id(cls, value: object) -> UUID:
        if not isinstance(value, str) or len(value) != 36 or str(parsed := UUID(value)) != value:
            raise ValueError("canonical report identity required")
        return parsed


class Capture(StrictModel):
    granted: Literal[True]
    policy_version: PolicyVersion
    client_id: ClientID | None = Field(repr=False)
    source_counter_id: SourceCounterID | None = None

    @field_validator("granted", mode="before")
    @classmethod
    def explicit_grant(cls, value: object) -> bool:
        if value is not True:
            raise ValueError("explicit consent required")
        return True


class Handoff(StrictModel):
    receipt: ReceiptToken = Field(repr=False)


class Pending(StrictModel):
    counter_id: Annotated[int, Field(strict=True, gt=0, le=MAX_COUNTER_ID)]
    policy_version: PolicyVersion
    client_id: ClientID | None = Field(repr=False)
    captured_at: AwareDatetime


class Empty(StrictModel):
    pass


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


class CollectorRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def handle(request: Request) -> Response:
            try:
                path = request.url.path
                if path.endswith("/events") and not settings.BUSINESS_MONITORING_ENABLED:
                    raise HTTPException(404)
                if path.endswith(("/capture", "/attach")) and approved_attribution_policy() is None:
                    raise HTTPException(404)
                if (
                    len(request.headers.getlist("origin")) != 1
                    or request.headers["origin"] not in settings.ALLOWED_ORIGINS
                    or request.headers["origin"] in ("null", "*")
                    or request.headers.getlist("x-analytics-request") != ["1"]
                    or request.headers.get("sec-fetch-site") not in (None, "same-origin")
                ):
                    raise HTTPException(403)
                media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if media_type != "application/json" or request.headers.get("content-encoding") not in (
                    None,
                    "identity",
                ):
                    raise HTTPException(415)
                if request.url.query:
                    raise HTTPException(422)
                data = bytearray()
                async for chunk in request.stream():
                    if len(data) + len(chunk) > _MAX_BODY:
                        raise HTTPException(413)
                    data.extend(chunk)
                request.state.analytics_body = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_pairs)
                route_model = _MODELS[path.rsplit("/", 1)[1]]
                request.state.analytics_body = route_model.model_validate(request.state.analytics_body)
                response = await original(request)
            except (ValidationError, ValueError, RecursionError):
                response = JSONResponse({"detail": "Invalid analytics request"}, status_code=422)
            except (RedisError, SQLAlchemyError):
                response = JSONResponse({"detail": "Analytics temporarily unavailable"}, status_code=503)
            except ClientDisconnect:
                response = JSONResponse({"detail": "Analytics request not accepted"}, status_code=400)
            except HTTPException as exc:
                response = JSONResponse(
                    {"detail": "Analytics request not accepted"}, exc.status_code, headers=exc.headers
                )
            response.headers.update(_HEADERS)
            return response

        return handle


router = APIRouter(prefix="/analytics", tags=["analytics"], route_class=CollectorRoute)
_MODELS: dict[str, type[StrictModel]] = {
    "events": ReportOpened,
    "capture": Capture,
    "attach": Handoff,
    "discard": Handoff,
    "revoke": Empty,
}


async def _limit(cache: Redis, scope: str, identity: str, maximum: int) -> None:
    key = sha256(identity.encode()).hexdigest()
    # Do not fall back to accepting events while the local abuse limit is unavailable.
    if int(await cache.eval(_RATE, 1, f"analytics:rate:{scope}:{key}")) > maximum:
        raise HTTPException(429, headers={"Retry-After": "60"})


def _receipt_key(receipt: str) -> str:
    return "analytics:pending:" + sha256(receipt.encode()).hexdigest()


def _client_address(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _request_schema(model: type[StrictModel]) -> dict[str, Any]:
    # Manual bounded streaming is intentional; still publish the exact DTO.
    return {"requestBody": {"required": True, "content": {"application/json": {"schema": model.model_json_schema()}}}}


@router.post("/events", status_code=204, openapi_extra=_request_schema(ReportOpened))
async def collect_event(request: Request, owner: Owner, db: DB, cache: Cache) -> Response:
    body: ReportOpened = request.state.analytics_body
    await _limit(cache, "event", str(owner), 30)
    if not await observe_owned_report(db, owner_id=owner, product=body.product, report_id=body.report_id):
        raise HTTPException(404)
    return Response(status_code=204)


@router.post("/attribution/capture", status_code=201, response_model=Handoff, openapi_extra=_request_schema(Capture))
async def capture_attribution(request: Request, cache: Cache) -> Handoff:
    """Accept a consent assertion only for the server's one approved version."""
    body: Capture = request.state.analytics_body
    await _limit(cache, "capture", _client_address(request), 20)
    policy = approved_attribution_policy()
    if (
        policy is None
        or body.policy_version != policy.version
        or body.source_counter_id != (str(policy.counter_id) if body.client_id is not None else None)
    ):
        raise HTTPException(404)
    receipt = secrets.token_urlsafe(32)
    pending = Pending(
        counter_id=policy.counter_id,
        policy_version=policy.version,
        client_id=body.client_id,
        captured_at=datetime.now(UTC),
    )
    await cache.set(_receipt_key(receipt), pending.model_dump_json(), ex=PENDING_SECONDS)
    return Handoff(receipt=receipt)


@router.post("/attribution/attach", status_code=204, openapi_extra=_request_schema(Handoff))
async def attach_attribution(request: Request, owner: Owner, db: DB, cache: Cache) -> Response:
    body: Handoff = request.state.analytics_body
    await _limit(cache, "attach", str(owner), 10)
    policy = approved_attribution_policy()
    if policy is None:
        raise HTTPException(404)
    raw = await cache.getdel(_receipt_key(body.receipt))
    if raw is None:
        raise HTTPException(404)
    try:
        pending = Pending.model_validate_json(raw)
    except ValidationError:
        raise HTTPException(404) from None
    now = datetime.now(UTC)
    if (
        pending.policy_version != policy.version
        or pending.counter_id != policy.counter_id
        or not receipt_is_fresh(pending.captured_at, now)
    ):
        raise HTTPException(404)
    await bind_attribution(
        db,
        owner_id=owner,
        policy=policy,
        client_id=pending.client_id,
        captured_at=pending.captured_at,
        now=now,
    )
    return Response(status_code=204)


@router.post("/attribution/discard", status_code=204, openapi_extra=_request_schema(Handoff))
async def discard_attribution(request: Request, cache: Cache) -> Response:
    body: Handoff = request.state.analytics_body
    await _limit(cache, "discard", _client_address(request), 20)
    await cache.delete(_receipt_key(body.receipt))
    return Response(status_code=204)


@router.post("/attribution/revoke", status_code=204, openapi_extra=_request_schema(Empty))
async def revoke_consent(owner: Owner, db: DB, cache: Cache) -> Response:
    # Revocation remains available when ingestion/approval is disabled.
    await _limit(cache, "revoke", str(owner), 10)
    await revoke_attribution(db, owner_id=owner, now=datetime.now(UTC))
    return Response(status_code=204)
